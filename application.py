from flask import Flask, render_template, request, redirect
import requests	# pip install requests
import json


response = requests.get('https://opentdb.com/api.php?amount=10')

print(response.status_code)
#print(response.content.decode('utf-8'))

data = response.content.decode('utf-8')
#print(data)
print('\n')

super_data = json.loads(data)
num_correct = 0 
print(type(super_data))

for i in super_data['results']:
	print('question: ' + i['question'])
	answers = i['incorrect_answers']
	answers.append(i['correct_answer'])
	print('list of choices:' + str(answers))
	print('correct ans: ' + i['correct_answer'])

	user_choice = input('whats ur answer pal\n')
	if user_choice == i['correct_answer']:
		print('berry nice')
		num_correct += 1
	else: 
		print('ur wrong')

print('u got ' + str(num_correct) + ' correct')
