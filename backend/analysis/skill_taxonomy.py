"""
Employmentmaxxing — Skill Taxonomy
Canonical skill mapping to normalize skill names across job descriptions.
"""

# Maps lowercase aliases → canonical name
SKILL_ALIASES: dict[str, str] = {
    # ── Programming Languages ─────────────────────────────────────
    "python": "Python",
    "python3": "Python",
    "py": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "c++": "C++",
    "cpp": "C++",
    "c/c++": "C/C++",
    "c": "C",
    "c#": "C#",
    "csharp": "C#",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "r": "R",
    "scala": "Scala",
    "julia": "Julia",
    "matlab": "MATLAB",
    "ruby": "Ruby",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "bash": "Bash",
    "shell": "Shell Scripting",
    "sql": "SQL",
    "haskell": "Haskell",

    # ── ML / AI Frameworks ────────────────────────────────────────
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "keras": "Keras",
    "jax": "JAX",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "hugging face": "Hugging Face",
    "huggingface": "Hugging Face",
    "transformers": "Hugging Face Transformers",
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    "opencv": "OpenCV",
    "spacy": "spaCy",
    "nltk": "NLTK",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scipy": "SciPy",
    "matplotlib": "Matplotlib",
    "mlflow": "MLflow",
    "wandb": "Weights & Biases",
    "weights and biases": "Weights & Biases",
    "ray": "Ray",
    "dask": "Dask",
    "onnx": "ONNX",
    "triton": "Triton",
    "vllm": "vLLM",
    "deepspeed": "DeepSpeed",
    "megatron": "Megatron",

    # ── Quantum Computing ─────────────────────────────────────────
    "qiskit": "Qiskit",
    "cirq": "Cirq",
    "pennylane": "PennyLane",
    "q#": "Q#",
    "qsharp": "Q#",
    "amazon braket": "Amazon Braket",
    "braket": "Amazon Braket",
    "quantinuum": "Quantinuum",
    "stim": "Stim",
    "quantum error correction": "Quantum Error Correction",
    "qec": "Quantum Error Correction",
    "vqe": "VQE",
    "qaoa": "QAOA",

    # ── Cloud & Infrastructure ────────────────────────────────────
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "Google Cloud",
    "google cloud": "Google Cloud",
    "google cloud platform": "Google Cloud",
    "azure": "Azure",
    "microsoft azure": "Azure",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "jenkins": "Jenkins",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "github actions": "GitHub Actions",
    "gitlab ci": "GitLab CI",
    "airflow": "Apache Airflow",
    "apache airflow": "Apache Airflow",
    "kafka": "Apache Kafka",
    "apache kafka": "Apache Kafka",
    "spark": "Apache Spark",
    "pyspark": "Apache Spark",
    "apache spark": "Apache Spark",
    "hadoop": "Hadoop",
    "databricks": "Databricks",

    # ── Databases ─────────────────────────────────────────────────
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "dynamodb": "DynamoDB",
    "cassandra": "Cassandra",
    "neo4j": "Neo4j",
    "sqlite": "SQLite",
    "bigquery": "BigQuery",
    "snowflake": "Snowflake",
    "pinecone": "Pinecone",
    "weaviate": "Weaviate",
    "chromadb": "ChromaDB",
    "chroma": "ChromaDB",
    "faiss": "FAISS",
    "pgvector": "pgvector",

    # ── Web / Frontend ────────────────────────────────────────────
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "vue": "Vue.js",
    "vue.js": "Vue.js",
    "vuejs": "Vue.js",
    "angular": "Angular",
    "svelte": "Svelte",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "express": "Express.js",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "spring": "Spring",
    "spring boot": "Spring Boot",
    "html": "HTML",
    "css": "CSS",
    "tailwind": "Tailwind CSS",
    "graphql": "GraphQL",
    "rest api": "REST APIs",
    "restful": "REST APIs",

    # ── AI / ML Concepts ──────────────────────────────────────────
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "dl": "Deep Learning",
    "natural language processing": "NLP",
    "nlp": "NLP",
    "computer vision": "Computer Vision",
    "cv": "Computer Vision",
    "reinforcement learning": "Reinforcement Learning",
    "rl": "Reinforcement Learning",
    "generative ai": "Generative AI",
    "gen ai": "Generative AI",
    "genai": "Generative AI",
    "llm": "LLMs",
    "llms": "LLMs",
    "large language model": "LLMs",
    "large language models": "LLMs",
    "rag": "RAG",
    "retrieval augmented generation": "RAG",
    "fine-tuning": "Fine-tuning",
    "finetuning": "Fine-tuning",
    "prompt engineering": "Prompt Engineering",
    "mlops": "MLOps",
    "data engineering": "Data Engineering",
    "data science": "Data Science",
    "data analysis": "Data Analysis",
    "a/b testing": "A/B Testing",
    "ab testing": "A/B Testing",
    "statistical analysis": "Statistical Analysis",
    "time series": "Time Series Analysis",

    # ── Tools & Practices ─────────────────────────────────────────
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "jira": "Jira",
    "linux": "Linux",
    "unix": "Unix/Linux",
    "agile": "Agile",
    "scrum": "Scrum",
    "microservices": "Microservices",
    "grpc": "gRPC",
    "protobuf": "Protocol Buffers",
    "cuda": "CUDA",
    "opengl": "OpenGL",
    "webgl": "WebGL",
    "latex": "LaTeX",
}

# Canonical skill → category mapping
SKILL_CATEGORIES: dict[str, str] = {
    "Python": "Programming Languages",
    "Java": "Programming Languages",
    "JavaScript": "Programming Languages",
    "TypeScript": "Programming Languages",
    "C++": "Programming Languages",
    "C": "Programming Languages",
    "Go": "Programming Languages",
    "Rust": "Programming Languages",
    "R": "Programming Languages",
    "SQL": "Programming Languages",
    "PyTorch": "ML/AI Frameworks",
    "TensorFlow": "ML/AI Frameworks",
    "JAX": "ML/AI Frameworks",
    "scikit-learn": "ML/AI Frameworks",
    "Hugging Face": "ML/AI Frameworks",
    "Qiskit": "Quantum Computing",
    "Cirq": "Quantum Computing",
    "PennyLane": "Quantum Computing",
    "AWS": "Cloud & Infrastructure",
    "Google Cloud": "Cloud & Infrastructure",
    "Azure": "Cloud & Infrastructure",
    "Docker": "Cloud & Infrastructure",
    "Kubernetes": "Cloud & Infrastructure",
    "React": "Web / Frontend",
    "Next.js": "Web / Frontend",
    "Node.js": "Web / Frontend",
    "Machine Learning": "AI/ML Concepts",
    "Deep Learning": "AI/ML Concepts",
    "NLP": "AI/ML Concepts",
    "Computer Vision": "AI/ML Concepts",
    "LLMs": "AI/ML Concepts",
}


def normalize_skill(skill: str) -> str:
    """Normalize a skill name to its canonical form."""
    key = skill.lower().strip()
    return SKILL_ALIASES.get(key, skill.strip())


def normalize_skills(skills: list[str]) -> list[str]:
    """Normalize a list of skills, removing duplicates."""
    seen = set()
    result = []
    for skill in skills:
        normalized = normalize_skill(skill)
        if normalized.lower() not in seen:
            seen.add(normalized.lower())
            result.append(normalized)
    return result


def get_skill_category(skill: str) -> str:
    """Get the category for a canonical skill name."""
    normalized = normalize_skill(skill)
    return SKILL_CATEGORIES.get(normalized, "Other")


def get_all_known_skills() -> list[str]:
    """Get all known canonical skill names for autocomplete."""
    return sorted(set(SKILL_ALIASES.values()))


if __name__ == "__main__":
    # Test normalization
    test_skills = ["pytorch", "tf", "k8s", "python3", "reactjs", "qiskit", "ml"]
    print("Normalized:", normalize_skills(test_skills))
    print(f"\nTotal known skills: {len(get_all_known_skills())}")
