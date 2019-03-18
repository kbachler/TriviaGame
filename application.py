from flask import Flask, render_template, make_response, request, redirect
from flask_login import LoginManager, UserMixin   # Manage user sessions
import requests, json, html, boto3, os
from boto3.dynamodb.conditions import Key, Attr
from random import shuffle

# Flask Login
application = Flask(__name__)

# Initialize AWS services
s3 = boto3.resource('s3')
db = boto3.resource('dynamodb', region_name='us-west-2')
db_client = boto3.client('dynamodb', region_name='us-west-2')
table = db.Table('triviadb2')

# Initialize our simple notification service:
sns = boto3.client('sns', region_name='us-west-2')

# Trivia game variables
# session_token = ''
# token = ''

def get_token():
  global session_token, token
  session_token = requests.get('https://opentdb.com/api_token.php?command=request')
  token = json.loads(session_token.content.decode('utf-8'))['token']

get_token()

uniqueIDs = dict()  # Dictionary for sessionIDs and session values
counter = 0         # Global counter for unique session IDs
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
question_num = 0

@application.route('/')
def initialize():
  return redirect('/home')

def check_session():
  id = request.cookies.get('session_id')    # Get the session_id, will be None if not existing

  # If id is set and returns back a valid ID
  if "session_"+str(id) in uniqueIDs:
    print("Session id already saved")
    return {"foundKey":True, "response": "session_"+str(id)} # response holds unique session id
  else:
    # If we don't, create one:
    global counter
    counter += 1             # Increment global counter for unique session ID
    my_id = str(counter)
    uniqueIDs["session_"+my_id] = {}    # Add to the end of our unique ID array
    print(uniqueIDs)
    resp = make_response(redirect('/home')) 
    resp.set_cookie(key='session_id', value=my_id)
    return {"foundKey": False, "response": resp} 

@application.route('/home')
def home():
  session_status = check_session()         # Get the session id
  if session_status["foundKey"]:
    return render_template('home.html', title='Home Page')
  else:
    return session_status["response"]        # Sets cookie and redirects

@application.route('/choose_category', methods=['POST'])
def choose_category():
  session_status = check_session()        # Get the session id
  if session_status["foundKey"]:
    category = request.form['choice']
    uniqueIDs[session_status["response"]] = {
          "current_category": category, 
          "num_times": 0, 
          "num_correct": 0,
          "num_total": 10, 
          "question_num": 0, 
          "category_data": {}
    }
    return redirect('/start_game')
  else:
    return session_status["response"]      # Sets cookie and redirects

# Starts the Trivia game instance
@application.route('/start_game')
def start_game():
  session_status = check_session()        # Get the session id
  if session_status["foundKey"]:
    session_info = uniqueIDs[session_status["response"]]
    if session_info["num_times"] >= session_info["num_total"] or session_info["question_num"] >= session_info["num_total"]:
      return render_template('user_creation.html', title='Create User')

    if not session_info["category_data"]:
      response = requests.get(category_list[session_info["current_category"]])
      data = response.content.decode('utf-8')
      session_info["category_data"] = json.loads(data)
      print(session_info["category_data"])

    # Resets token if questions are all exhausted
    if session_info["category_data"]['response_code'] == 4:
      global session_token, token
      session_token = requests.get('https://opentdb.com/api_token.php?command=reset&token=' + str(token))
      token = json.loads(session_token.content.decode('utf-8'))['token']
      response = requests.get(category_list[session_info["category"]])
      data = response.content.decode('utf-8')
      session_info["category_data"] = json.loads(data)
      
    # Resets token if 6+ hours of inactivity
    if session_info["category_data"]['response_code'] == 3:
      get_token()
      response = requests.get(category_list[session_info["category"]])
      data = response.content.decode('utf-8')
      session_info["category_data"] = json.loads(data)

    answers = []

    question = html.unescape(session_info["category_data"]['results'][session_info["question_num"]]['question'])
    for i in session_info["category_data"]['results'][session_info["question_num"]]['incorrect_answers']:
      answers.append(html.unescape(i))
    correct_answer = html.unescape(session_info["category_data"]['results'][session_info["question_num"]]['correct_answer'])
    answers.append(correct_answer)
    shuffle(answers)
    session_info["question_num"] += 1
    return render_template('start_game.html', title='Game Start', question=question,
                ans1=answers[0], ans2=answers[1], ans3=answers[2],
                ans4=answers[3], correct_answer=correct_answer,
                question_num=session_info["question_num"])
  else:
    return session_status["response"]      # Sets cookie and redirects

# Checks to see if user's answer is correct or not
@application.route('/check_answer', methods=['POST'])
def check_answer():
  session_status = check_session()        # Get the session id
  if session_status["foundKey"]:
    session_info = uniqueIDs[session_status["response"]]
    correct_answer = request.form['correct_answer']
    # For testing purposes
    print('YOUR INPUT: ' + request.form['ans'])
    print('REAL ANS: ' + request.form['correct_answer'])
    if request.form['ans'] == correct_answer:
      session_info["num_correct"] += 1
    
    session_info["num_times"] += 1
    return redirect('/start_game')
  else:
    return session_status["response"]      # Sets cookie and redirects

# Prints the user's game results
@application.route('/results')
def print_results():
  session_status = check_session()        # Get the session id
  if session_status["foundKey"]:
    session_info = uniqueIDs[session_status["response"]]  
    return render_template('results.html', title='Results', 
							num_correct=session_info["num_correct"], num_times=session_info["num_times"])
  else:  
    return session_status["response"]      # Sets cookie and redirects

# Creates the user account to store info in various AWS services
# and keep track of their high score
@application.route('/user_creation', methods=['POST'])
def create_user():
  session_status = check_session()        # Get the session id
  if session_status["foundKey"]:
    session_info = uniqueIDs[session_status["response"]]  
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    phone_number = request.form['phone_number']

    # If user puts in no info for user creation, just wants result
    if first_name == '' or last_name == '' or phone_number == '':
      return redirect('/results') 

    number = '+1' + phone_number
    print(number)
    sns.publish(PhoneNumber = number, Message='Hi ' + first_name + '! Thank you for creating an account with Trivia Game :) Play again soon, okay?' )

    # Upload entry into DB if score > prior high score
    db_entry = {}
    row = table.scan(FilterExpression=Attr('phone_number').eq(phone_number))

    # If item does not exist in table
    if row['Count'] == 0:
      db_entry['phone_number'] = phone_number
      db_entry['first_name'] = first_name
      db_entry['last_name'] = last_name
      db_entry['highscore'] = session_info["num_correct"]
      table.put_item(Item=db_entry)
    else:
      prior_highscore = row['Items'][0]['highscore']
      if session_info["num_correct"] > prior_highscore:
        table.update_item(
          Key={'phone_number':phone_number},
          UpdateExpression='set highscore=:highscore',
          ExpressionAttributeValues={':highscore': session_info["num_correct"]},
          ReturnValues='UPDATED_NEW'
        )
    return redirect('/results')
  else:  
    return session_status["response"]      # Sets cookie and redirects

@application.route('/check_score', methods=['POST'])
def check_score():
	# scan DB for entry
  phone_number = request.form['phone_number']
  if phone_number == '':
    return redirect('/home')
    
  row = table.scan(FilterExpression=Attr('phone_number').eq(phone_number))
	
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
	return redirect('/home')

if __name__ == "__main__":
  application.run(debug=True)