from mycroft import MycroftSkill, intent_file_handler
from datetime import datetime, timedelta, time, timezone
import caldav
import creds
from mycroft.util.parse import extract_datetime
import importlib


class Nextcalendar(MycroftSkill):
	def __init__(self):
		MycroftSkill.__init__(self)


	# reads user and password, which are stored in the creds.py file, to access nextcloud (from next.social-robot.info)
	# returns a list of all calendars of the user
	def get_calendars(self):
		url = f"https://{creds.user}:{creds.pw}@next.social-robot.info/nc/remote.php/dav"

		client = caldav.DAVClient(url)
		principal = client.principal()
		calendars = principal.calendars()
		return calendars


	# uses the calendars list returned from get_calendars and searches for the calendar specified in the creds file
	# returns the calendar object or asks for the correct calendar name (if it can't find a fitting calendar)
	def get_calendar(self):
		calendars = self.get_calendars()
		calendar = next((cal for cal in calendars if cal.name.lower() == creds.cal_name.lower()), None)
		if calendar is None:
			self.change_calendar(f"You don't have an calendar called {creds.cal_name}. "
								 f"Please tell me another existing calendar name")
		else:
			return calendar	
	

	# takes a calendar object as parameter
	# returns a list of all events (event objects) stored in the calendar, which are lying in the future
	def get_future_events(self, calendar):
		future_events = calendar.date_search(start=datetime.now())
		future_events = [i for i in future_events if
						 i.instance.vevent.dtstart.value.astimezone() > datetime.now(timezone.utc).astimezone()]
		return future_events
		

	# takes a string as parameter, which contains the phrase mycroft should tell the user to ask for a date
	# repeats the request, if it can't extract a date from the users input
	# returns the extracted datetime object
	def get_datetime_from_user(self, response_text):
		user_input = self.get_response(response_text)
		extracted_datetime = extract_datetime(user_input)
		if extracted_datetime is None:
			return self.get_datetime_from_user("Couldnt understand the time stamp. Please try again")
		else:
			return extracted_datetime[0]
			

	# takes a event object as parameter
	# asks the user, which attribute(s) should get changed until the user doesn't want to change anything
	# saves the modified event
	def modify_event(self, to_edit_event):
		change_att = self.get_response(f"Found appointment {to_edit_event.instance.vevent.summary.value}. "
									   f"Which attribute do you want to change?")
		if change_att == "start":
			# start = self.get_response("When should it start?")
			# to_edit_event.instance.vevent.dtstart.value = extract_datetime(start)[0]
			to_edit_event.instance.vevent.dtstart.value = self.get_datetime_from_user("When should it start?")
			to_edit_event.save()
			self.speak(f"Successfully modified your appointment")
		elif change_att == "end":
			# end = self.get_response("When should it end?")
			# to_edit_event.instance.vevent.dtend.value = extract_datetime(end)[0]
			to_edit_event.instance.vevent.dtend.value = self.get_datetime_from_user("When should it end?")
			to_edit_event.save()
			self.speak(f"Successfully modified your appointment")
		elif change_att == "name":
			name = self.get_response("How should I call it?")
			to_edit_event.instance.vevent.summary.value = name
			to_edit_event.save()
			self.speak(f"Successfully modified your appointment")
		again = self.get_response(f"Do you want to change another attribute?")
		if again == "yes":
			self.modify_event(to_edit_event)


	# takes a string as parameter, which contains the phrase mycroft should tell the user to ask for a calendar name
	# changes and saves the cal_name value in the creds file and reimports it
	def change_calendar(self, response_text):
		cal_name = self.get_response(response_text)
		if next((cal for cal in self.get_calendars() if cal.name.lower() == cal_name.lower()), None) is None:
			self.change_calendar(f"You don't have an calendar called {cal_name}. "
								 f"Please tell me another existing calendar name")
		else:
			creds_file = open("creds.py", "r")
			list_of_lines = creds_file.readlines()
			list_of_lines[2] = f"cal_name = '{cal_name}'"

			creds_file = open("creds.py", "w")
			creds_file.writelines(list_of_lines)
			creds_file.close()
			importlib.reload(creds)
			self.speak(f"Successfully changed to calendar {cal_name}")


	# gets executed after user inputs, which asks mycroft to change the calendar
	# calls change_calendar method to change the used calendar
	@intent_file_handler('change.intent')
	def handle_change(self, message):
		self.change_calendar("Tell me the name of the calendar you want to use")	


	# gets executed after user inputs, which asks mycroft to inform the user about his next appointment
	@intent_file_handler('nextcalendar.intent')
	def handle_nextcalendar(self, message):
		calendar = self.get_calendar()

		# get list of all upcoming events
		future_events = self.get_future_events(calendar)

		if (len(future_events) == 0):
			self.speak("You haven't got an upcoming appointment")
		else:
			# sort events by their start date
			future_events.sort(key=lambda x: x.instance.vevent.dtstart.value.astimezone())

			# getting the earliest event and its important values
			earliest_appointment = future_events[0].instance.vevent
			start = (earliest_appointment.dtstart.value)
			summary = (earliest_appointment.summary.value)

			# get list of all appointments with the earliest start date
			next_appointments = [i for i in future_events if
							 i.instance.vevent.dtstart.value.astimezone() == start.astimezone()]

			# check whether mulltiple appointments start at the date and create according answers
			if len(next_appointments)>1:
				first_appointments_string = " ".join(x.instance.vevent.summary.value + ", "
													 for x in next_appointments[:-1])
				self.speak(f"You've got multiple next appointments, which are starting at "
						   f"{(start).strftime('%B')} {(start).strftime('%d')}, {(start).strftime('%y')} at "
						   f"{(start).strftime('%H:%M')} and are entitled {first_appointments_string}and "
						   f"{next_appointments[-1].instance.vevent.summary.value}.")
			else:
				output = f"Your next appointment is on {(start).strftime('%B')} {(start).strftime('%d')}, " \
						 f"{(start).strftime('%y')} at {(start).strftime('%H:%M')} and is entitled {summary}."
				self.speak(output)


	# gets executed after user inputs, which asks mycroft to create a new appointment
	@intent_file_handler('create.intent')
	def handle_create(self, message):
		calendar = self.get_calendar()

		# get attributes for new appointment from user
		name = self.get_response("How should I call it?")
		startdate = self.get_datetime_from_user("When should it start").strftime("%Y%m%dT%H%M%S")
		enddate = self.get_datetime_from_user("When should it end").strftime("%Y%m%dT%H%M%S")

		createdate = datetime.now().strftime("%Y%m%dT%H%M%S")

		# summarize all information in a string to add the new event
		new_event = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTAMP:{createdate}
DTSTART:{startdate}
DTEND:{enddate}
SUMMARY:{name}
END:VEVENT
END:VCALENDAR
"""

		calendar.add_event(new_event)
		self.speak(f"Succesfully created a new event called {name}")


	# gets executed after user inputs, which asks mycroft to create a new appointment
	@intent_file_handler('delete.intent')
	def handle_delete(self, message):
		calendar = self.get_calendar()
		future_events = self.get_future_events(calendar)

		# ask the user for the name of the event
		to_delete_name = self.get_response("How is the event called?")

		# get list for all upcoming events with the specified name
		matches = [ev for ev in future_events if ev.instance.vevent.summary.value.lower() == to_delete_name.lower()]

		# checking if one, none or multiple matches are found and handling the different szenarios
		if len(matches)==0:
			self.speak(f"Can't find an appoinment called {to_delete_name}")
		elif len(matches)>1:
			to_delete_date = self.get_datetime_from_user(f"found multiple appointments called "
														 f"{to_delete_name}. Tell me on what date and time it should"
														 f" get deleted.").astimezone()
			to_delete_event = [ev for ev in matches if ev.instance.vevent.dtstart.value.astimezone() == to_delete_date]
			if len(to_delete_event)==0:
				self.speak(f"Can't find an appointment called {to_delete_name} at {to_delete_date}.")
			else:
				to_delete_event[0].delete()
				self.speak(f"Succesfully deleted the appointment {to_delete_name}")
		elif len(matches)==1:
			matches[0].delete()
			self.speak(f"Succesfully deleted the appointment {to_delete_name}")


	# gets executed after user inputs, which asks mycroft to modify an existing appointment
	@intent_file_handler("modify.intent")
	def handle_modify(self, message):
		calendar = self.get_calendar()
		future_events = self.get_future_events(calendar)

		# asks user for the event name
		to_edit_name = self.get_response("How is the event called?")
		# get list of events with the specified name
		matches = [ev for ev in future_events if ev.instance.vevent.summary.value.lower() == to_edit_name.lower()]

		# checking if one, none or multiple matches are found and handling the different szenarios
		if len(matches)==0:
			to_edit_event = None
			self.speak(f"Can't find an appoinment called {to_edit_name}")
		elif len(matches)>1:
			to_edit_date = self.get_datetime_from_user(f"found multiple appointments called "
													   f"{to_delete_name}. Tell me on what date and time it should "
													   f"get modified.").astimezone()
			to_edit_event = [ev for ev in matches if ev.instance.vevent.dtstart.value.astimezone() == to_edit_date]
			if len(to_edit_event)==0:
				self.speak(f"Couldnt find an appointment called {to_edit_name} at {to_edit_date}.")
				to_edit_event = None
			else:
				to_edit_event = to_edit_event[0]
		elif len(matches)==1:
			to_edit_event = matches[0]

		# checking if a match was found and calling the modify_event method to change the events attributes
		if type(to_edit_event) == caldav.objects.Event:
			self.modify_event(to_edit_event)
			
	
	
def create_skill():
    return Nextcalendar()