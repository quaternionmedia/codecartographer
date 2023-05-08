import os
import nox


def inject_js_to_coverage_report(js_file, coverage_dir):
    index_html_path = os.path.join(coverage_dir, "index.html")
    with open(index_html_path, "r") as f:
        index_html = f.read()

    with open(js_file, "r") as f:
        js_content = f.read()

    updated_html = index_html.replace(
        "</body>", f"<script>{js_content}</script></body>"
    )
    with open(index_html_path, "w") as f:
        f.write(updated_html)


# tests on python 3.8, 3.9 and 3.11
@nox.session(python=["3.8", "3.9", "3.11"])
def unit_tests(session):
    session.install(".")
    session.install("matplotlib")  # needed to close the matplot show window
    session.install(
        "pytest", "pytest-html", "pytest-cov"
    )  # needed to run pytest and pytest extensions
    session.run(
        "pytest",
        "tests",
        "--confcutdir=tests/test_reports",
        "--cov=codecarto",
        "--cov-report=html:tests/test_reports/coverage",
        "--html=tests/test_reports/report.html",
        "--css=tests/test_reports/codecarto.css",
    )
    inject_js_to_coverage_report(
        "tests/test_reports/add_link.js", "tests/test_reports/coverage"
    )


@nox.session()
def cleanup(session):
    session.run("nox", "-r")
