# used to customize pytest html report
import os

# def pytest_html_report_title(report):
#     # get coverage path, in the directory above this one
#     coverage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "coverage")
#     # get coverage index.html path
#     coverage_index_path = os.path.join(coverage_path, "index.html")
#     # get coverage link
#     coverage_link = f'<a href="{coverage_index_path}">Coverage Report</a>'
#     report.title = f"{report.title} - {coverage_link}"

def pytest_html_results_summary(prefix, summary, postfix): 
    # get coverage path, in the directory above this one
    coverage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "coverage")
    # get coverage index.html path
    coverage_index_path = os.path.join(coverage_path, "index.html")
    # get coverage link
    coverage_link = f'<a href="{coverage_index_path}">Coverage Report</a>'
    prefix.append(f"<h1>Test Report - {coverage_link}</h1>")

# def pytest_html_report_title(report):
#     report.title = "CodeCartographer Test Report"
#     report.head.append('<a href="coverage/index.html">Coverage Report</a>')