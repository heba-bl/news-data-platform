import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

MIN_CONTENT_LENGTH = 100
MIN_TITLE_LENGTH = 5


class QualityReport:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.issues: List[Dict] = []

    def add_issue(self, article_url: str, issue_type: str, detail: str):
        self.issues.append(
            {"url": article_url, "issue_type": issue_type, "detail": detail}
        )
        self.failed += 1

    def summary(self) -> Dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.passed / self.total * 100, 2) if self.total else 0,
            "issues_count": len(self.issues),
        }


def check_article(article: Dict) -> Tuple[bool, List[str]]:
    issues = []

    title = article.get("title", "")
    if not title or len(title.strip()) < MIN_TITLE_LENGTH:
        issues.append("TITLE_EMPTY_OR_TOO_SHORT")

    published_at = article.get("published_at", "")
    if not published_at or published_at in ("N/A", "", "null", None):
        issues.append("DATE_MISSING")

    content = article.get("content", "")
    if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
        issues.append("CONTENT_TOO_SHORT")

    url = article.get("url", "")
    if not url or not url.startswith("http"):
        issues.append("URL_INVALID")

    source = article.get("source", "")
    if not source:
        issues.append("SOURCE_MISSING")

    return (len(issues) == 0), issues


def run_quality_checks(articles: List[Dict]) -> Tuple[List[Dict], QualityReport]:
    report = QualityReport()
    valid_articles = []

    for article in articles:
        report.total += 1
        passed, issues = check_article(article)
        if passed:
            report.passed += 1
            valid_articles.append(article)
        else:
            for issue in issues:
                report.add_issue(
                    article.get("url", "unknown"),
                    issue,
                    f"Article from {article.get('source', 'unknown')}",
                )

    logger.info(f"Quality check: {report.summary()}")
    if report.issues:
        logger.warning(f"Quality issues found: {len(report.issues)}")
        for issue in report.issues[:5]:
            logger.warning(f"  [{issue['issue_type']}] {issue['url'][:80]}")

    return valid_articles, report


def check_completeness(articles: List[Dict]) -> Dict:
    fields = ["title", "author", "published_at", "category", "content", "source", "url"]
    result = {}
    total = len(articles)
    if total == 0:
        return {}

    for field in fields:
        filled = sum(1 for a in articles if a.get(field) and str(a[field]).strip())
        result[field] = {"filled": filled, "total": total, "rate": round(filled / total * 100, 2)}

    return result


def check_coherence(articles: List[Dict]) -> Dict:
    issues = []
    for article in articles:
        source = article.get("source", "")
        lang = article.get("language", "")
        if source in ("Hespress", "Akhbarona") and lang not in ("ar", "fr", "unknown"):
            issues.append({"url": article.get("url"), "issue": f"Unexpected lang {lang} for {source}"})
        content = article.get("content", "")
        title = article.get("title", "")
        if content and title and title.lower() not in content[:500].lower() and len(content) < 200:
            issues.append({"url": article.get("url"), "issue": "Title not found in short content"})

    return {"coherence_issues": len(issues), "samples": issues[:5]}
