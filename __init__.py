from mycroft import MycroftSkill, intent_file_handler
from datetime import datetime, timedelta, time, timezone
import caldav
import creds
from mycroft.util.parse import extract_datetime
import importlib


class Nextcalendar(MycroftSkill):
	"""A Collection of useful funktions and five mycroft skills

	This class provides five Mycorft skills which are all related to a nextcloud calendar.
	The first skill allows the user to change the calendar on which the actions will apply.
	The second skill allows the user to ask for the next upcoming Appointment.
	The third skill allows the user to create an Appointment.
	The fourth skill allows the user to delete an Appointment.
	The fifth skill allows the user to modify an Appointment.
	The last skill allows the user to get the Appointments of a specific day.
	"""

	def __init__(self):
		"""Inits class"""
		MycroftSkill.__init__(self)


	# reads user and password, which are stored in the creds.py file, to access nextcloud (from next.social-robot.info)
	# returns a list of all calendars of the user
	def get_calendars(self):
		"""Gets calendars from CalDav-Url.

		Returns:
			A list of calendars.
		"""
		url = f"https://{creds.user}:{creds.pw}@next.social-robot.info/nc/remote.php/dav"

		client = caldav.DAVClient(url)
		principal = client.principal()
		calendars = principal.calendars()
		return calendars


	# uses the calendars list returned from get_calendars and searches for the calendar specified in the creds file
	# returns the calendar object or asks for the correct calendar name (if it can't find a fitting calendar)
	def get_calendar(self):
		"""Gets calendar from calendars with the set name

		Returns:
			A calendar.
		"""
		calendars = self.get_calendars()
		calendar = next((cal for cal in calendars if cal.name.lower() == creds.cal_name.lower()), None)
		if calendar is None:
			self.change_calendar(f"You don't have an calendar called {creds.cal_name}. "
								 f"Please tell me another existing calendar name")
		else:
			return calendar

	# takes a calendar object as parameter
	# optional parameters start and end datime objects, which specify when the event should start
	# respects the time values of the start and end parameters
	# returns a list of all events (event objects) stored in the calendar, which are lying in the future
	def get_events(self, calendar, start: datetime = None, end: datetime = None):
		"""Gets all events between start and end time.

		Args:
			calendar:
				A calendar object where the events are stored.
			start:
				Optional; A datetime object representing the start time.
			end:
				Optional; A datetime object representing the end time.

		Returns:
			 A filtered list of the events in the given time span.
		"""
		if start is None:
			return calendar.events()
		if start is not None:
			filtered_events = calendar.date_search(start=start, end=end)
			filtered_events = [i for i in filtered_events if
							   i.instance.vevent.dtstart.value.astimezone() >= start.astimezone()]
			if end is not None:
				filtered_events = [i for i in filtered_events if
								   i.instance.vevent.dtstart.value.astimezone() <= end.astimezone()]
			return filtered_events


	# takes a string as parameter, which contains the phrase mycroft should tell the user to ask for a date
	# repeats the request, if it can't extract a date from the users input
	# returns the extracted datetime object
	def get_datetime_from_user(self, response_text: str):
		"""Gets the input of the user and parse it to a datetime.

		Args:
			response_text: A string representing the phrase said by Mycroft.

		Returns:
			If the string couldn't be parsed the function calls it self another time.

			A datetime object.
		"""
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
		"""modifies an event object.

		Args: A event object representing the modified object.
		"""
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
	def change_calendar(self, response_text: str):
		"""Changes the calendar from nextcloud on which the actions of the functions are performed
		by changing and saving the cal_name value in the creds file and reimporting it.

		Args:
			response_text:
				A string representing the phrase said by Mycroft.
		"""
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
		"""Handles the change an event skill.
		"""
		self.change_calendar("Tell me the name of the calendar you want to use")


	# gets executed after user inputs, which asks mycroft to inform the user about his next appointment
	@intent_file_handler('nextcalendar.intent')
	def handle_nextcalendar(self, message):
		"""Informs the User about the next upcoming event.
		"""
		calendar = self.get_calendar()

		# get list of all upcoming events
		future_events = self.get_events(calendar, datetime.now().astimezone())

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
		"""Creates an event with given name, start date and end date.
		"""
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
		"""Deletes an event with given name.
		If more than one event exists with given name the date will be added to the filter.
		"""
		calendar = self.get_calendar()
		future_events = self.get_events(calendar)

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
		"""Modifies an event with given name.
		If more than one event exists with the given name the date will be added to the filter.
		"""
		calendar = self.get_calendar()
		future_events = self.get_events(calendar)

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


	@intent_file_handler("getday.intent")
	def handle_getday(self, message):
		"""Informs the user of the events on a specific day.
		"""
		calendar = self.get_calendar()

		to_edit_date = self.get_datetime_from_user("Tell me the date.")

		starttime = to_edit_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone()

		endtime = to_edit_date.replace(hour=23, minute=59, second=59, microsecond=999).astimezone()

		future_events = self.get_events(calendar, starttime.astimezone(), endtime.astimezone())

		matches = [ev for ev in future_events if ev.instance.vevent.dtstart.value.astimezone() == to_edit_date]

		if len(matches) == 0:
			self.speak(f"Couldnt find an appointment at {to_edit_date.strftime('%B')} {to_edit_date.strftime('%d')} "
					   f"{to_edit_date.strftime('%y')}.")
		elif len(matches) == 1:
			# self.speak(f"I've found one appointment at {to_edit_date}.")
			start = (matches[0].dtstart.value)
			summary = (matches[0].summary.value)
			output = f"You've got one appointment on {(start).strftime('%B')} {(start).strftime('%d')}, " \
					 f"{(start).strftime('%y')} at {(start).strftime('%H:%M')} and it is entitled {summary}."
			self.speak(output)
		elif len(matches) > 1:
			appointments_string = " ".join(x.instance.vevent.summary.value + ", "
												 for x in matches[:-1])
			self.speak(f"I've found more than one appointment at {to_edit_date.strftime('%B')} "
					   f"{to_edit_date.strftime('%d')} {(start).strftime('%y')}. They are entitled "
					   f"{appointments_string}and {matches[-1].instance.vevent.summary.value}.")



def create_skill():
    return Nextcalendar()