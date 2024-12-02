import pyrebase
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify

# Configuração do Firebase para Realtime Database e Autenticação
config = {
    "apiKey": "AIzaSyBKiSzxLmYteE9chx55sOpZE2wJG7T6Z6s",
    "authDomain": "cookbook-b0616.firebaseapp.com",
    "databaseURL": "https://cookbook-b0616-default-rtdb.firebaseio.com",
    "projectId": "cookbook-b0616",
    "storageBucket": "cookbook-b0616.appspot.com",
    "messagingSenderId": "177929491194",
    "appId": "1:177929491194:web:28a540a0d338240dcfef43"
}

# Inicializa o Pyrebase para autenticação e Realtime Database #aqui
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()
storage = firebase.storage()

loggedUser = None

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'  # Chave para sessões e mensagens de flash

# Rota de Login
@app.route('/', methods=['GET', 'POST'])
def index():
    global loggedUser 
    # global userToken
    if request.method == 'POST':
        # fetch informations
        usuario = request.form['usuario']
        senha = request.form['senha']

        try:
            # Autentica o usuário
            loggedUser = auth.sign_in_with_email_and_password(usuario, senha)
        except:
            # reload page
            flash('Username or password incorrect!')  # Mensagem de erro
            return redirect(url_for('index'))

        return redirect(url_for('home'))
    
    else:
        return render_template('index.html')


@app.route('/logout', methods=['POST'])
def logout():
    global loggedUser
    loggedUser = None  # Clear user session
    flash("You have successfully logged out!")  # Success message
    return redirect(url_for('index'))  # Redirect to login page


# Criação de conta de usuário e armazenamento no Realtime Database
@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        # fetch informations
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        # Validação de senha
        if len(senha) < 6:
            flash('The password must be at least 6 characters long.')
            return render_template('create_account.html')

        # create data set
        data = {
            'nome': nome,
            'email': email,
            'senha': senha,  # Evite armazenar senhas em texto simples na produção
            'recipes': {}
        }

        try:
            # Criar usuário com o Firebase Authentication
            user = auth.create_user_with_email_and_password(email, senha)

        except Exception as e:
            if "email" in str(e).lower() and "exists" in str(e).lower():
                flash('This email is already being used. Try logging in or use another email.')
                return render_template('create_account.html')
            else:
                flash('Something went wrong. Try again later')
                return render_template('create_account.html')
            
        db.child('users').child(user['localId']).set(data)

        flash("Account created!")
        return redirect(url_for('index'))  # Redireciona para a página de login
    else:
        return render_template('create_account.html')


# Página de receitas com busca (Firestore)  #aqui
@app.route('/home', methods=['GET'])
def home():
    global loggedUser
    loggedUser['idToken'] = auth.refresh(loggedUser['refreshToken'])['idToken']

    # Fetch all recipes
    recipes = db.child("users").child(loggedUser['localId']).child('recipes').get()
    
    # Pass recipes as values while rendering page
    return render_template("home.html", recipes=recipes.val())
    

@app.route('/search', methods=['POST'])
def search():
    global loggedUser
    loggedUser['idToken'] = auth.refresh(loggedUser['refreshToken'])['idToken']

    matches = dict()
    filtered = dict()

    search = request.form.get('search')

    if search == '':
        flash('No match found')
        return redirect(url_for('home'))
    
    recipes = db.child("users").child(loggedUser['localId']).child('recipes').get()

    for i in recipes.each():
        if i.val()['title'].lower().find(search.lower()) != -1:
            matches[i.key()] = i.val()['title']

    if len(matches) == 0:
        flash('No match found')
        return redirect(url_for('home'))

    for key in matches:
        filtered[key] = recipes.val()[key]

    return render_template("home.html", recipes=filtered)


# Criação de receita e upload de imagem #aqui
@app.route('/createRecipe', methods=['GET', 'POST'])
def createRecipe():
    global loggedUser
    loggedUser['idToken'] = auth.refresh(loggedUser['refreshToken'])['idToken']

    if request.method == 'POST':
        # fetch informations
        title = request.form.get('title')
        ingredients = request.form.get('ingredients')
        time = request.form.get('time')
        instructions = request.form.get('instructions')
        category = request.form.get('category')

        # Dados da receita para o Firestore
        recipe_data = {
            "title": title,
            "ingredients": ingredients,
            "time": time,
            "instructions": instructions,
            "category": category
        }

        ingredients = []

        # Add recipe to user profile
        try:
            db.child("users").child(loggedUser['localId']).child('recipes').push(recipe_data, loggedUser['idToken'])
            flash('Recipe created')
            return redirect(url_for('home'))
        except :
            flash("Error when creating the recipe")
            return redirect(url_for('home'))
    else:
        return render_template('createRecipe.html')


    

@app.route('/edit_recipe/<recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    global loggedUser
    loggedUser['idToken'] = auth.refresh(loggedUser['refreshToken'])['idToken']

    if request.method == 'POST':
        # Coleta os dados do formulário
        title = request.form['title']
        ingredients = request.form['ingredients']
        time = request.form['time']
        instructions = request.form['instructions']
        category = request.form['category']

        # Atualiza os dados da receita no Firebase
        updated_recipe_data = {
            "title": title,
            "ingredients": ingredients,
            "time": time,
            "instructions": instructions,
            "category": category
        }

        try:
            db.child("users").child(loggedUser['localId']).child('recipes').child(recipe_id).update(updated_recipe_data, loggedUser['idToken'])
            flash("Recipe updated!")
        except:
            flash("Error when updating the recipe.")

        return redirect(url_for('home'))

    else:
        # Busca a receita específica no Firebase Realtime Database
        recipe = db.child("users").child(loggedUser['localId']).child('recipes').child(recipe_id).get()

        if recipe.val() is None:
            flash("Recipe not found.")
            return redirect(url_for('home'))

        # Renderiza o template edit_recipe.html com os dados da receita
        return render_template("editRecipe.html", recipe=recipe.val(), recipe_id=recipe_id)
        # return render_template("edit_recipe.html", recipe=recipe.val(), recipe_id=recipe_id)
    

@app.route('/delete_recipe/<recipe_id>', methods=['GET'])
def delete_recipe(recipe_id):
    global loggedUser
    loggedUser['idToken'] = auth.refresh(loggedUser['refreshToken'])['idToken']

    # Attempt to delete the recipe from Firebase
    try:
        db.child("users").child(loggedUser['localId']).child('recipes').child(recipe_id).remove(loggedUser['idToken'])
        flash('Recipe deleted successfully.')
    except:
        flash('An error occurred while deleting the recipe.')

    return redirect(url_for('home'))  # Redirect to the home page after deletion
    


if __name__ == '__main__':
    app.run(debug=True)
