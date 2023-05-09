// used to add a link to the pytest report page to go back to the main report page

document.addEventListener('DOMContentLoaded', function () {
    var header = document.querySelector('div#header');
    if (header) {
        var link = document.createElement('a');
        link.href = '../report.html';
        link.innerText = 'Back to Pytest Report';
        link.style.marginLeft = '20px';
        header.appendChild(link);
    }
});
