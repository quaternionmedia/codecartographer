# used to customize pytest html report

def pytest_html_report_title(report):
    report.title = "CodeCartographer Test Report"
    report.head.append('<a href="coverage_html/index.html">Coverage Report</a>')
