"""
Tests for Spark Big Data Processing Simulator.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from processing_engine import (
    Partition,
    Partitioner,
    MapReduceEngine,
    word_count,
    AggregationPipeline,
    DataSkewDetector,
    generate_sample_data,
)


class TestPartition:
    def test_partition_creation(self):
        p = Partition(0, [1, 2, 3])
        assert len(p) == 3
        assert p.partition_id == 0

    def test_partition_repr(self):
        p = Partition(1, [10, 20])
        assert "id=1" in repr(p)
        assert "size=2" in repr(p)


class TestPartitioner:
    def test_default_partitions(self):
        pt = Partitioner(4)
        parts = pt.partition(list(range(100)))
        assert len(parts) == 4
        total = sum(len(p) for p in parts)
        assert total == 100

    def test_single_partition(self):
        pt = Partitioner(1)
        parts = pt.partition([1, 2, 3])
        assert len(parts) == 1
        assert len(parts[0]) == 3

    def test_invalid_partitions(self):
        with pytest.raises(ValueError):
            Partitioner(0)

    def test_key_function(self):
        data = [{"key": "a", "val": 1}, {"key": "b", "val": 2}]
        pt = Partitioner(2)
        parts = pt.partition(data, key_fn=lambda x: x["key"])
        total = sum(len(p) for p in parts)
        assert total == 2


class TestMapReduceEngine:
    def test_basic_map_reduce(self):
        engine = MapReduceEngine(num_partitions=2)
        data = [1, 2, 3, 4, 5]
        mapper = lambda x: [("total", x)]
        reducer = lambda k, vs: (k, sum(vs))
        results = engine.run(data, mapper, reducer)
        assert len(results) == 1
        assert results[0][1] == 15

    def test_map_phase(self):
        engine = MapReduceEngine()
        parts = [Partition(0, ["hello world"]), Partition(1, ["foo bar"])]
        mapper = lambda text: [(w, 1) for w in text.split()]
        mapped = engine.map_phase(parts, mapper)
        assert len(mapped) == 4

    def test_shuffle_sort(self):
        engine = MapReduceEngine()
        mapped = [("a", 1), ("b", 2), ("a", 3)]
        shuffled = engine.shuffle_sort(mapped)
        assert shuffled["a"] == [1, 3]
        assert shuffled["b"] == [2]

    def test_reduce_phase(self):
        engine = MapReduceEngine()
        shuffled = {"x": [1, 2], "y": [3]}
        reducer = lambda k, vs: (k, sum(vs))
        results = engine.reduce_phase(shuffled, reducer)
        result_dict = dict(results)
        assert result_dict["x"] == 3
        assert result_dict["y"] == 3


class TestWordCount:
    def test_single_text(self):
        result = word_count(["hello world hello"])
        assert result["hello"] == 2
        assert result["world"] == 1

    def test_multiple_texts(self):
        result = word_count(["big data", "data processing", "big processing"])
        assert result["big"] == 2
        assert result["data"] == 2
        assert result["processing"] == 2

    def test_empty_input(self):
        result = word_count([])
        assert result == {}

    def test_punctuation_handling(self):
        result = word_count(["hello, world! hello."])
        assert result["hello"] == 2
        assert result["world"] == 1


class TestAggregationPipeline:
    @pytest.fixture
    def sample_data(self):
        return [
            {"region": "North", "category": "A", "amount": 100},
            {"region": "North", "category": "B", "amount": 200},
            {"region": "South", "category": "A", "amount": 150},
            {"region": "South", "category": "B", "amount": 250},
            {"region": "East", "category": "A", "amount": 50},
        ]

    def test_filter(self, sample_data):
        pipe = AggregationPipeline(sample_data)
        result = pipe.filter(lambda r: r["region"] == "North").execute()
        assert len(result) == 2

    def test_group_by_sum(self, sample_data):
        pipe = AggregationPipeline(sample_data)
        result = pipe.group_by("region").aggregate("amount", "sum").execute()
        totals = {r["region"]: r["amount_sum"] for r in result}
        assert totals["North"] == 300
        assert totals["South"] == 400

    def test_group_by_avg(self, sample_data):
        pipe = AggregationPipeline(sample_data)
        result = pipe.group_by("region").aggregate("amount", "avg").execute()
        avgs = {r["region"]: r["amount_avg"] for r in result}
        assert avgs["North"] == 150
        assert avgs["East"] == 50

    def test_group_by_count(self, sample_data):
        pipe = AggregationPipeline(sample_data)
        result = pipe.group_by("region").aggregate("amount", "count").execute()
        counts = {r["region"]: r["amount_count"] for r in result}
        assert counts["North"] == 2
        assert counts["South"] == 2
        assert counts["East"] == 1

    def test_limit(self, sample_data):
        pipe = AggregationPipeline(sample_data)
        result = pipe.limit(2).execute()
        assert len(result) == 2

    def test_chained_operations(self, sample_data):
        pipe = AggregationPipeline(sample_data)
        result = (
            pipe.filter(lambda r: r["amount"] > 100)
                .group_by("region")
                .aggregate("amount", "sum")
                .execute()
        )
        assert all(r["amount_sum"] > 100 for r in result)


class TestDataSkewDetector:
    def test_balanced_partitions(self):
        partitions = [Partition(i, list(range(25))) for i in range(4)]
        result = DataSkewDetector.analyze_partition_skew(partitions)
        assert not result["is_skewed"]
        assert result["skew_ratio"] == 1.0

    def test_skewed_partitions(self):
        partitions = [
            Partition(0, list(range(90))),
            Partition(1, list(range(5))),
            Partition(2, list(range(3))),
            Partition(3, list(range(2))),
        ]
        result = DataSkewDetector.analyze_partition_skew(partitions)
        assert result["is_skewed"]
        assert result["max_size"] == 90

    def test_empty_partitions(self):
        result = DataSkewDetector.analyze_partition_skew([])
        assert not result["is_skewed"]

    def test_key_skew_detection(self):
        data = [("hot_key", i) for i in range(90)] + [("cold", i) for i in range(10)]
        result = DataSkewDetector.detect_key_skew(data)
        assert result["has_hot_keys"]
        assert result["hot_keys"][0]["key"] == "hot_key"

    def test_no_key_skew(self):
        data = [(f"key_{i % 10}", i) for i in range(100)]
        result = DataSkewDetector.detect_key_skew(data)
        assert not result["has_hot_keys"]


class TestSampleDataGenerator:
    def test_generate_default(self):
        data = generate_sample_data()
        assert len(data) == 1000

    def test_custom_size(self):
        data = generate_sample_data(n=50)
        assert len(data) == 50

    def test_record_fields(self):
        data = generate_sample_data(n=1)
        record = data[0]
        assert "id" in record
        assert "category" in record
        assert "region" in record
        assert "amount" in record
        assert "quantity" in record

    def test_reproducible(self):
        d1 = generate_sample_data(seed=123)
        d2 = generate_sample_data(seed=123)
        assert d1 == d2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
