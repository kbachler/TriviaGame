from flask import Flask, render_template, request, redirect
from flask_login import LoginManager 
import requests, json, html, boto3, os
from boto3.dynamodb.conditions import Key, Attr
from random import shuffle


# Flask Login
application = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(application)

# Initialize AWS services
s3 = boto3.resource('s3')
db = boto3.resource('dynamodb', region_name='us-west-2')
db_client = boto3.client('dynamodb', region_name='us-west-2')
table = db.Table('triviadb')

# Trivia game variables
session_token = requests.get('https://opentdb.com/api_token.php?command=request')
token = json.loads(session_token.content.decode('utf-8'))['token']

num_times = 0
num_correct = 0 
num_total = 10
response = ''
category = ''
category_list = {
				'Anime':'https://opentdb.com/api.php?amount=10&category=31&type=multiple&token=' + token,
				'Video Games':'https://opentdb.com/api.php?amount=10&category=15&type=multiple&token=' + token,
				'Random':'https://opentdb.com/api.php?amount=10&type=multiple&token=' + token,
				'Film':'https://opentdb.com/api.php?amount=10&category=11&type=multiple&token=' + token,
				'Music':'https://opentdb.com/api.php?amount=10&category=12&type=multiple&token=' + token,
				'Animals':'https://opentdb.com/api.php?amount=10&category=27&type=multiple&token=' + token,
				'Mythology':'https://opentdb.com/api.php?amount=10&category=20&type=multiple&token=' + token
				}
category_chosen = False
question_num = 0

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@application.route('/login', methods=['GET', 'POST'])
def login():
    # Here we use a class of some kind to represent and validate our
    # client-side form data. For example, WTForms is a library that will
    # handle this for us, and we use a custom LoginForm to validate.
    form = LoginForm()
    if form.validate_on_submit():
        # Login and validate the user.
        # user should be an instance of your `User` class
        login_user(user)

        flask.flash('Logged in successfully.')

        next = flask.request.args.get('next')
        # is_safe_url should check if the url is safe for redirects.
        # See http://flask.pocoo.org/snippets/62/ for an example.
        if not is_safe_url(next):
            return flask.abort(400)

        return flask.redirect(next or flask.url_for('index'))
    return flask.render_template('login.html', form=form)

@application.route('/')
def initialize():
	return redirect('/home')

@application.route('/home')
def home():
	return render_template('home.html', title='Home Page')

@application.route('/choose_category', methods=['POST'])
def choose_category():
	global category
	category = request.form['choice']
	return redirect('/start_game')

# Starts the Trivia game instance
@application.route('/start_game')
def start_game():
	global category, category_chosen, response, question_num
	if num_times >= num_total:
		return render_template('user_creation.html', title='Create User')

	if category_chosen == False:
		response = requests.get(category_list[category])
		category_chosen = True

	data = response.content.decode('utf-8')
	api_response = json.loads(data)
	answers = []
	question = html.unescape(api_response['results'][question_num]['question'])
	for i in api_response['results'][question_num]['incorrect_answers']:
		answers.append(html.unescape(i))
	correct_answer = html.unescape(api_response['results'][question_num]['correct_answer'])
	answers.append(correct_answer)
	shuffle(answers)
	question_num += 1
	return render_template('start_game.html', title='Game Start', question=question, \
							ans1=answers[0], ans2=answers[1], ans3=answers[2], 		 \
							ans4=answers[3], correct_answer=correct_answer,
							bg_image='pingu.jpg')

# Checks to see if user's answer is correct or not
@application.route('/check_answer', methods=['POST'])
def check_answer():
	global num_times, num_correct
	correct_answer = request.form['correct_answer']
	# For testing purposes
	print('YOUR INPUT: ' + request.form['ans'])
	print('REAL ANS: ' + request.form['correct_answer'])
	if request.form['ans'] == correct_answer:
		num_correct += 1

	num_times += 1
	return redirect('/start_game')

# Prints the user's game results
@application.route('/results')
def print_results():
	global num_times, num_correct
	return render_template('results.html', title='Results', \
							num_correct=num_correct, num_times=num_times)

# Creates the user account to store info in various AWS services
# and keep track of their high score
@application.route('/user_creation', methods=['POST'])
def create_user():
	first_name = request.form['first_name']
	last_name = request.form['last_name']
	email = request.form['email']

	user_data = s3.Object('css490trivia', 'rawuserdata.txt')
	list = user_data.get()['Body'].read().decode('utf-8').splitlines()
	f = open('rawuserdata.txt', 'a')
	for line in list:
		f.write(line + '\n')
	f.write(first_name + ',' + last_name + ',' + email + ',' + str(num_correct) + '\n')

	# Upload file to S3 bucket
	#user_data.upload_file('rawuserdata.txt')
	
	# Upload entry into DB if score > prior high score
	db_entry = {}
	row = table.scan(FilterExpression=Attr('email').eq(email))

	# If item does not exist in table
	if row['Count'] == 0:
		db_entry['email'] = email
		db_entry['first_name'] = first_name
		db_entry['last_name'] = last_name
		db_entry['highscore'] = num_correct
		table.put_item(Item=db_entry)
	else:
		prior_highscore = row['Items'][0]['highscore']
		if num_correct > prior_highscore:
			table.update_item(
				Key={'email':email},
				UpdateExpression='set highscore=:highscore',
				ExpressionAttributeValues={':highscore': num_correct},
				ReturnValues='UPDATED_NEW'
			)

	# Delete file locally
	f.close()
	#os.remove('rawuserdata.txt')

	return redirect('/results')

@application.route('/check_score', methods=['POST'])
def check_score():
	# scan DB for entry
	email = request.form['email']
	row = table.scan(FilterExpression=Attr('email').eq(email))
	
	# If user does not exist
	if len(row) == 0 or row['Count'] == 0:
		return render_template('score.html', title='Your Score', \
							highscore='absolutely nothing')

	highscore = row['Items'][0]['highscore']
	return render_template('score.html', title='Your Score', \
							highscore=highscore)

@application.route('/leaderboard')
def display_leaderboard():
	score_list = []
	if table.scan()['Count'] == 0:
		redirect('/home')

	items = table.scan()['Items']

	for item in items:
		#print(item)
		score_list.append(item)
	
	# Bubble sort
	for i in range(len(score_list) - 1, 0, -1):
		for x in range(i):
			val1 = int(score_list[x]['highscore'])
			val2 = int(score_list[x + 1]['highscore'])
			if val1 > val2:
				temp = score_list[x]
				score_list[x] = score_list[x + 1]
				score_list[x + 1] = temp

	# Reverse list to get descending order of scores
	score_list.reverse()

	return render_template('leaderboard.html', title='Leaderboard', \
					 first_name1=score_list[0]['first_name'], \
					 last_name1=score_list[0]['last_name'], \
					 highscore1=score_list[0]['highscore'], \
					 first_name2=score_list[1]['first_name'], \
					 last_name2=score_list[1]['last_name'], \
					 highscore2=score_list[1]['highscore'], \
					 first_name3=score_list[2]['first_name'], \
					 last_name3=score_list[2]['last_name'], \
					 highscore3=score_list[2]['highscore'], \
					 first_name4=score_list[3]['first_name'], \
					 last_name4=score_list[3]['last_name'], \
					 highscore4=score_list[3]['highscore'], \
					 first_name5=score_list[4]['first_name'], \
					 last_name5=score_list[4]['last_name'], \
					 highscore5=score_list[4]['highscore'])


# Restarts the game instance
@application.route('/reset', methods=['POST'])
def reset():
	global num_times, num_correct, category_chosen, question_num
	num_times = 0
	num_correct = 0
	category_chosen = False
	question_num = 0
	return redirect('/home')

if __name__ == "__main__":
	application.run(debug=True)