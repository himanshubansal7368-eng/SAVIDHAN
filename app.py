
import json
import os
import re

import numpy as np
from flask import Flask, jsonify, render_template, request
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

DATA_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "constitution.jsonl"
)

documents = []
vectorizer = None
document_matrix = None


def load_documents():
    global documents, vectorizer, document_matrix

    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}. "
            "Place constitution.jsonl beside app.py."
        )

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            text = str(record.get("text") or "").strip()
            if not text:
                continue

            documents.append({
                "title": str(record.get("title") or "Untitled"),
                "text": text,
                "url": str(record.get("url") or ""),
                "kind": str(record.get("kind") or "document"),
                "part_name": str(record.get("part_name") or ""),
            })

    if not documents:
        raise ValueError("No usable documents found in JSONL.")

    # Combine titles with page text to improve retrieval.
    corpus = [
        doc["title"] + "\n" + doc["text"]
        for doc in documents
    ]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        max_features=30000,
        sublinear_tf=True
    )

    document_matrix = vectorizer.fit_transform(corpus)

    print(f"Loaded {len(documents)} constitutional documents.")


def make_snippet(text, query, max_length=700):
    """Choose a useful paragraph rather than always showing page beginnings."""
    paragraphs = [
        re.sub(r"\s+", " ", p).strip()
        for p in re.split(r"[\n\r]+", text)
        if p.strip()
    ]

    if not paragraphs:
        return text[:max_length]

    terms = set(re.findall(r"\w+", query.lower()))
    stop_words = {
        "what", "which", "where", "when", "does", "about",
        "the", "and", "for", "are", "is", "of", "in", "to",
        "how", "can", "tell", "me", "under", "explain"
    }
    terms -= stop_words

    def paragraph_score(paragraph):
        words = set(re.findall(r"\w+", paragraph.lower()))
        return len(terms & words)

    best = max(paragraphs, key=paragraph_score)
    if len(best) < 80:
        best = " ".join(paragraphs[:3])

    if len(best) > max_length:
        best = best[:max_length].rsplit(" ", 1)[0] + "…"

    return best


def search_documents(query, top_k=5):
    query_vector = vectorizer.transform([query])

    if query_vector.nnz == 0:
        return []

    scores = cosine_similarity(
        query_vector, document_matrix
    ).ravel()

    # Boost exact Article-number/title matches when the user
    # explicitly asks about an Article.
    match = re.search(r"\barticle\s+(\d+[a-z]?)\b", query, re.I)
    if match:
        article_number = match.group(1).lower()
        for i, doc in enumerate(documents):
            title = doc["title"].lower()
            if re.search(
                rf"\barticle\s+{re.escape(article_number)}\b",
                title
            ):
                scores[i] += 0.5

    indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for index in indices:
        doc = documents[int(index)]

        results.append({
            "title": doc["title"],
            "kind": doc["kind"],
            "part_name": doc["part_name"],
            "url": doc["url"],
            "snippet": make_snippet(doc["text"], query),
            "score": round(float(scores[index]), 4)
        })

    return results


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/ask", methods=["POST"])
def ask():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question") or "").strip()

    if not question:
        return jsonify({"error": "Please enter a question."}), 400

    if len(question) > 1000:
        return jsonify({
            "error": "Please keep your question under 1000 characters."
        }), 400

    results = search_documents(question, top_k=5)

    if not results:
        return jsonify({
            "question": question,
            "answer": (
                "I could not find a strong text match. "
                "Try different keywords or a specific Article number."
            ),
            "results": []
        })

    answer = (
        "I found the following potentially relevant constitutional "
        "documents in the available dataset. Review the source text "
        "before relying on an interpretation."
    )

    return jsonify({
        "question": question,
        "answer": answer,
        "results": results
    })


if __name__ == "__main__":
    load_documents()
    app.run(host="127.0.0.1", port=5000, debug=False)
