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
        "pytest", "pytest-html", "pytest-cov", "pytest-xdist"
    )  # needed to run pytest and pytest extensions
    session.run(
        "python", "-m", "cProfile", "-o", "profile_output.pstats",
        "-m", "pytest",  
        "tests",
        "-n", "4",
        "--confcutdir=tests/test_reports/assets",
        "--cov=codecarto",
        "--cov-report=html:tests/test_reports/coverage",
        "--html=tests/test_reports/report.html",
        "--css=tests/test_reports/assets/codecarto.css",
    )
    inject_js_to_coverage_report(
        "tests/test_reports/assets/add_link.js", "tests/test_reports/coverage"
    )

# can use this to test a specific file
# nox -s debug 
@nox.session(python=["3.11"])
def debug(session):
    file_path = "tests/test_cli/test_cli_palette/test_cli_palette_new.py"
    session.install(".") 
    session.install("matplotlib")  # needed to close the matplot show window
    session.install(
        "pytest", "pytest-html", "pytest-cov", "pytest-xdist"
    )  # needed to run pytest and pytest extensions
    session.run(
        "python", "-m", "cProfile", "-o", "profile_output.pstats",
        "-m", "pytest",  "-vv",
        file_path,
        "-n", "4",
        "--confcutdir=tests/test_reports/assets",
        "--cov=codecarto",
        "--cov-report=html:tests/test_reports/coverage",
        "--html=tests/test_reports/report.html",
        "--css=tests/test_reports/assets/codecarto.css",
        )

