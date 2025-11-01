from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__, template_folder='../templates/main')

@main_bp.route('/')
@main_bp.route('/index')
def index():
    """Serves the homepage."""
    return render_template('index.html', title='Home')

# We will add other public routes like '/about' here later