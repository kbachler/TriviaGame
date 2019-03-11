from flask import Flask, render_template, request, redirect
import requests, json, html
from random import shuffle

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

@application.route('/start_game')
def start_game():
	if num_times == num_total:
		return redirect('/results')

	response = requests.get('https://opentdb.com/api.php?amount=1&type=multiple')
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

@application.route('/results')
def print_results():
	global num_times, num_correct
	return render_template('results.html', title='Results', num_correct=num_correct, num_times=num_times)

@application.route('/reset', methods=['POST'])
def reset():
	global num_times, num_correct
	num_times = 0
	num_correct = 0
	return redirect('/home')

if __name__ == "__main__":
	application.run(debug=True)