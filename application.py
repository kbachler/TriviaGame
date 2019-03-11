from flask import Flask, render_template, request, redirect
import requests, json, html, boto3, os
from boto3.dynamodb.conditions import Key, Attr
from random import shuffle

# Initialize AWS services
s3 = boto3.resource('s3')
db = boto3.resource('dynamodb', region_name='us-west-2')
db_client = boto3.client('dynamodb', region_name='us-west-2')
#table = db.Table('css490prog4')

# Trivia game variables
num_times = 0
num_correct = 0 
num_total = 3
application = Flask(__name__)

@application.route('/')
def initialize():
	return redirect('/home')

@application.route('/home')
def home():
	return render_template('home.html', title='Home Page')

# Starts the Trivia game instance
@application.route('/start_game')
def start_game():
	if num_times == num_total:
		return render_template('user_creation.html', title='Create User')
		#return redirect('/user_creation') # Needs to redirect to user creation which redirects to results

	response = requests.get('https://opentdb.com/api.php?amount=' + str(num_total) + \
							'&type=multiple')
	data = response.content.decode('utf-8')
	api_response = json.loads(data)
	print(api_response)
	answers = []
	question = html.unescape(api_response['results'][0]['question'])
	for i in api_response['results'][0]['incorrect_answers']:
		answers.append(html.unescape(i))
	correct_answer = html.unescape(api_response['results'][0]['correct_answer'])
	answers.append(correct_answer)
	shuffle(answers)

	return render_template('start_game.html', title='Game Start', question=question, \
							ans1=answers[0], ans2=answers[1], ans3=answers[2], 		 \
							ans4=answers[3], correct_answer=correct_answer)

# Checks to see if user's answer is correct or not
@application.route('/check_answer', methods=['POST'])
def check_answer():
	if 'ans' not in request.form:
		redirect('/start_game')
	global num_times, num_correct
	correct_answer = request.form['correct_answer']
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
	user_data.upload_file('rawuserdata.txt')
	
	# Delete file locally
	f.close()
	os.remove('rawuserdata.txt')

	return redirect('/results')


def maintain_scores():
	user_data = s3.Object('css490trivia', 'rawuserdata.txt')
	list = user_data.get()['Body'].read().decode('utf-8').splitlines()
	f = open('userdata.txt', 'a')
	for line in list:
		# Info[0] = 'David'
		
		info = line.split(',')


# Restarts the game instance
@application.route('/reset', methods=['POST'])
def reset():
	global num_times, num_correct
	num_times = 0
	num_correct = 0
	return redirect('/home')

if __name__ == "__main__":
	application.run(debug=True)