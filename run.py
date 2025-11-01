from agroadvisor import create_app, db
from agroadvisor.models import User, Product, Role

# Create the application instance using the factory
app = create_app()

@app.shell_context_processor
def make_shell_context():
    """
    Makes 'db', 'User', 'Product', and 'Role' available 
    in the 'flask shell' for easy testing.
    """
    return {'db': db, 'User': User, 'Product': Product, 'Role': Role}

if __name__ == '__main__':
    app.run(debug=True)