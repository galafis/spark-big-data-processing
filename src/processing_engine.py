"""
Big Data Processing Framework Simulator

Implements MapReduce, partitioned data processing, shuffle/sort simulation,
word count, aggregation pipelines, and data skew detection without requiring
a real Spark installation.

Author: Gabriel Demetrios Lafis
"""

import hashlib
import math
import random
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    TypeVar,
)

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


# ── Partition helpers ─────────────────────────────────────────────────

class Partition:
    """Represents a data partition (similar to an RDD partition)."""

    def __init__(self, partition_id: int, data: List[Any]):
        self.partition_id = partition_id
        self.data = list(data)

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return f"Partition(id={self.partition_id}, size={len(self.data)})"


class Partitioner:
    """Partition data across a fixed number of buckets."""

    def __init__(self, num_partitions: int = 4):
        if num_partitions < 1:
            raise ValueError("num_partitions must be >= 1")
        self.num_partitions = num_partitions

    def partition(self, data: List[Any], key_fn: Callable[[Any], Any] = None) -> List[Partition]:
        """Distribute *data* across partitions using hash-based assignment."""
        buckets: Dict[int, List[Any]] = {i: [] for i in range(self.num_partitions)}
        for item in data:
            k = key_fn(item) if key_fn else item
            bucket = int(hashlib.md5(str(k).encode()).hexdigest(), 16) % self.num_partitions
            buckets[bucket].append(item)
        return [Partition(pid, items) for pid, items in buckets.items()]


# ── MapReduce engine ──────────────────────────────────────────────────

class MapReduceEngine:
    """Simplified MapReduce engine operating on in-memory partitions."""

    def __init__(self, num_partitions: int = 4, num_workers: int = 2):
        self.num_partitions = num_partitions
        self.num_workers = num_workers
        self.partitioner = Partitioner(num_partitions)

    def map_phase(
        self,
        partitions: List[Partition],
        mapper: Callable[[Any], Iterable[Tuple[K, V]]],
    ) -> List[Tuple[K, V]]:
        """Apply *mapper* to every element in every partition."""
        mapped: List[Tuple[K, V]] = []
        for part in partitions:
            for item in part.data:
                mapped.extend(mapper(item))
        return mapped

    def shuffle_sort(self, mapped: List[Tuple[K, V]]) -> Dict[K, List[V]]:
        """Group values by key (shuffle) and sort keys."""
        grouped: Dict[K, List[V]] = defaultdict(list)
        for key, value in mapped:
            grouped[key].append(value)
        return dict(sorted(grouped.items(), key=lambda x: str(x[0])))

    def reduce_phase(
        self,
        shuffled: Dict[K, List[V]],
        reducer: Callable[[K, List[V]], Any],
    ) -> List[Any]:
        """Apply *reducer* to each (key, values) group."""
        results = []
        for key, values in shuffled.items():
            results.append(reducer(key, values))
        return results

    def run(
        self,
        data: List[Any],
        mapper: Callable[[Any], Iterable[Tuple[K, V]]],
        reducer: Callable[[K, List[V]], Any],
    ) -> List[Any]:
        """Execute the full MapReduce pipeline."""
        partitions = self.partitioner.partition(data)
        mapped = self.map_phase(partitions, mapper)
        shuffled = self.shuffle_sort(mapped)
        return self.reduce_phase(shuffled, reducer)


# ── Word Count (classic) ─────────────────────────────────────────────

def word_count(texts: List[str], num_partitions: int = 4) -> Dict[str, int]:
    """Classic MapReduce word count over a list of text strings."""

    def mapper(text: str) -> List[Tuple[str, int]]:
        return [(w.lower().strip(".,!?;:\"'"), 1) for w in text.split() if w.strip(".,!?;:\"'")]

    def reducer(key: str, values: List[int]) -> Tuple[str, int]:
        return (key, sum(values))

    engine = MapReduceEngine(num_partitions=num_partitions)
    results = engine.run(texts, mapper, reducer)
    return {k: v for k, v in results}


# ── Aggregation Pipeline ─────────────────────────────────────────────

class AggregationPipeline:
    """Fluent API for chaining aggregation operations on list-of-dict data."""

    def __init__(self, data: List[Dict[str, Any]]):
        self._data = list(data)
        self._stages: List[Tuple[str, Any]] = []

    def filter(self, predicate: Callable[[Dict], bool]) -> "AggregationPipeline":
        self._stages.append(("filter", predicate))
        return self

    def group_by(self, key: str) -> "AggregationPipeline":
        self._stages.append(("group_by", key))
        return self

    def aggregate(self, field: str, func: str = "sum") -> "AggregationPipeline":
        self._stages.append(("aggregate", (field, func)))
        return self

    def sort(self, key: str, reverse: bool = False) -> "AggregationPipeline":
        self._stages.append(("sort", (key, reverse)))
        return self

    def limit(self, n: int) -> "AggregationPipeline":
        self._stages.append(("limit", n))
        return self

    def execute(self) -> List[Dict[str, Any]]:
        """Run all registered stages and return the result."""
        result = list(self._data)

        group_key: Optional[str] = None
        agg_ops: List[Tuple[str, str]] = []

        for stage_type, param in self._stages:
            if stage_type == "filter":
                result = [r for r in result if param(r)]
            elif stage_type == "group_by":
                group_key = param
            elif stage_type == "aggregate":
                agg_ops.append(param)
            elif stage_type == "sort":
                field, rev = param
                result = sorted(result, key=lambda x: x.get(field, 0), reverse=rev)
            elif stage_type == "limit":
                result = result[: param]

        if group_key and agg_ops:
            groups: Dict[Any, List[Dict]] = defaultdict(list)
            for row in result:
                groups[row.get(group_key)].append(row)

            agg_result = []
            for gk, rows in groups.items():
                entry: Dict[str, Any] = {group_key: gk}
                for field, func in agg_ops:
                    vals = [r.get(field, 0) for r in rows]
                    if func == "sum":
                        entry[f"{field}_{func}"] = sum(vals)
                    elif func == "avg":
                        entry[f"{field}_{func}"] = sum(vals) / len(vals) if vals else 0
                    elif func == "count":
                        entry[f"{field}_{func}"] = len(vals)
                    elif func == "min":
                        entry[f"{field}_{func}"] = min(vals) if vals else None
                    elif func == "max":
                        entry[f"{field}_{func}"] = max(vals) if vals else None
                agg_result.append(entry)

            # Apply any remaining sort/limit to aggregated result
            for stage_type, param in self._stages:
                if stage_type == "sort":
                    field, rev = param
                    agg_result = sorted(agg_result, key=lambda x: x.get(field, 0), reverse=rev)
                elif stage_type == "limit":
                    agg_result = agg_result[: param]
            result = agg_result

        return result


# ── Data Skew Detector ────────────────────────────────────────────────

class DataSkewDetector:
    """Detect data skew across partitions or key distributions."""

    @staticmethod
    def analyze_partition_skew(partitions: List[Partition]) -> Dict[str, Any]:
        """Compute partition-level skew statistics."""
        sizes = [len(p) for p in partitions]
        if not sizes:
            return {"skew_ratio": 0, "is_skewed": False}
        avg = sum(sizes) / len(sizes)
        max_size = max(sizes)
        min_size = min(sizes)
        skew_ratio = max_size / avg if avg > 0 else 0
        variance = sum((s - avg) ** 2 for s in sizes) / len(sizes)
        std_dev = math.sqrt(variance)
        coefficient_of_variation = std_dev / avg if avg > 0 else 0
        return {
            "partition_sizes": sizes,
            "mean_size": round(avg, 2),
            "max_size": max_size,
            "min_size": min_size,
            "std_dev": round(std_dev, 2),
            "skew_ratio": round(skew_ratio, 2),
            "coefficient_of_variation": round(coefficient_of_variation, 4),
            "is_skewed": skew_ratio > 2.0,
        }

    @staticmethod
    def detect_key_skew(data: List[Tuple[Any, Any]], top_n: int = 5) -> Dict[str, Any]:
        """Detect hot-keys that receive disproportionate volume."""
        counter = Counter(k for k, _ in data)
        total = sum(counter.values())
        top_keys = counter.most_common(top_n)
        hot_keys = []
        for key, count in top_keys:
            pct = count / total * 100 if total > 0 else 0
            hot_keys.append({"key": key, "count": count, "percentage": round(pct, 2)})
        return {
            "total_records": total,
            "unique_keys": len(counter),
            "hot_keys": hot_keys,
            "has_hot_keys": hot_keys[0]["percentage"] > 25 if hot_keys else False,
        }


# ── Convenience helpers ──────────────────────────────────────────────

def generate_sample_data(n: int = 1000, categories: int = 5, seed: int = 42) -> List[Dict[str, Any]]:
    """Generate sample data records for testing pipelines."""
    rng = random.Random(seed)
    cats = [f"cat_{i}" for i in range(categories)]
    regions = ["North", "South", "East", "West"]
    return [
        {
            "id": i,
            "category": rng.choice(cats),
            "region": rng.choice(regions),
            "amount": round(rng.uniform(10, 1000), 2),
            "quantity": rng.randint(1, 100),
        }
        for i in range(n)
    ]
