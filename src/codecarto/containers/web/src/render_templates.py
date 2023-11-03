from jinja2 import Environment, FileSystemLoader, select_autoescape

# Set up Jinja2 environment
env = Environment(
    loader=FileSystemLoader("src/pages"),
    autoescape=select_autoescape(["html", "xml"]),
)

# Define your context if needed (pass data to your templates)
context = {
    # 'key': 'value', # Your context variables here
}

# Render home.html as index.html
template = env.get_template("home/home.html")
rendered = template.render(context)

# Write the rendered template to the output directory
with open("web/src/pages/index.html", "w") as f:
    f.write(rendered)
