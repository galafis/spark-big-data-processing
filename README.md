# Spark Big Data Processing

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![PySpark](https://img.shields.io/badge/PySpark-E25A1C?style=for-the-badge&logo=apachespark&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=for-the-badge&logo=jupyter&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![License-MIT](https://img.shields.io/badge/License--MIT-yellow?style=for-the-badge)


Framework simulador de processamento de big data inspirado no Apache Spark. Implementa MapReduce, particionamento de dados, shuffle/sort, word count, pipelines de agregacao e deteccao de data skew -- tudo sem dependencias externas de big data.

Big data processing framework simulator inspired by Apache Spark. Implements MapReduce, data partitioning, shuffle/sort, word count, aggregation pipelines, and data skew detection -- all without external big data dependencies.

---

## Arquitetura / Architecture

```mermaid
graph LR
    subgraph Input["Entrada / Input"]
        D1[Raw Data]
        D2[Text Files]
    end

    subgraph Partitioning["Particionamento"]
        P1[Hash Partitioner]
        P2[Partition 0]
        P3[Partition 1]
        P4[Partition N]
    end

    subgraph MapReduce["MapReduce Engine"]
        M1[Map Phase] --> S1[Shuffle & Sort]
        S1 --> R1[Reduce Phase]
    end

    subgraph Analytics["Analise"]
        A1[Aggregation Pipeline]
        A2[Data Skew Detector]
        A3[Word Count]
    end

    D1 --> P1
    D2 --> P1
    P1 --> P2
    P1 --> P3
    P1 --> P4
    P2 --> M1
    P3 --> M1
    P4 --> M1
    R1 --> A1
    R1 --> A2
    R1 --> A3
```

## Fluxo MapReduce / MapReduce Flow

```mermaid
sequenceDiagram
    participant Client
    participant Partitioner
    participant MapPhase
    participant ShuffleSort
    participant ReducePhase

    Client->>Partitioner: partition(data)
    Partitioner-->>MapPhase: List of Partitions
    MapPhase->>MapPhase: Apply mapper to each element
    MapPhase-->>ShuffleSort: List of (key, value) pairs
    ShuffleSort->>ShuffleSort: Group by key, sort
    ShuffleSort-->>ReducePhase: Dict of key -> values
    ReducePhase->>ReducePhase: Apply reducer per key
    ReducePhase-->>Client: Final results
```

## Funcionalidades / Features

| Funcionalidade / Feature | Descricao / Description |
|---|---|
| MapReduce Engine | Motor MapReduce com map, shuffle/sort e reduce / MapReduce engine with map, shuffle/sort and reduce phases |
| Partitioner | Particionamento hash-based configuravel / Configurable hash-based data partitioning |
| Word Count | Contagem de palavras classica via MapReduce / Classic word count via MapReduce |
| Aggregation Pipeline | API fluente para agregacoes encadeadas / Fluent API for chained aggregations (sum, avg, count, min, max) |
| Data Skew Detector | Deteccao de skew em particoes e hot-keys / Partition skew and hot-key detection |
| Sample Data Generator | Gerador de dados para testes / Test data generator with reproducible seeds |

## Inicio Rapido / Quick Start

```python
from src.processing_engine import word_count, AggregationPipeline, generate_sample_data

# Word Count
counts = word_count(["hello world hello", "world of data"])
# {'data': 1, 'hello': 2, 'of': 1, 'world': 2}

# Aggregation Pipeline
data = generate_sample_data(n=500)
result = (
    AggregationPipeline(data)
    .filter(lambda r: r["amount"] > 100)
    .group_by("region")
    .aggregate("amount", "sum")
    .sort("amount_sum", reverse=True)
    .execute()
)
```

## Testes / Tests

```bash
pytest tests/ -v
```

## Tecnologias / Technologies

- Python 3.9+
- pytest

## Licenca / License

MIT License - veja [LICENSE](LICENSE) / see [LICENSE](LICENSE).
