from mycroft import MycroftSkill, intent_file_handler
from datetime import datetime, timedelta, time, timezone, date
import caldav
import creds
from mycroft.util.parse import extract_datetime
import importlib


class Nextcalendar(MycroftSkill):
    """A Collection of useful functions and five mycroft intent handlers

	This class provides a Mycorft skill containing five intent handlers which are all related to a nextcloud calendar.
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


    def get_calendars(self):
        """Gets calendars from CalDav-Url. Creates the used caldav-url by joining the user, password and url values
        stored in the creds.py file in the mycroft-core directory.

		Returns:
			A list of calendars.
		"""
        # combining the username, password and nextcloud url (saved in local creds file)
        url = f"https://{creds.user}:{creds.pw}@{creds.url}/nc/remote.php/dav"
        client = caldav.DAVClient(url)
        principal = client.principal()
        calendars = principal.calendars()
        return calendars


    def get_calendar(self):
        """Gets calendar from calendars list by filtering for the name value set in the creds file.
        Asks the user for another calendar name, if no fitting calendar was found

		Returns:
			A calendar containing the correct name attribute.
		"""
        calendars = self.get_calendars()
        # search for first occuring calendar object in list containing the correct name value
        calendar = next((cal for cal in calendars if cal.name.lower() == creds.cal_name.lower()), None)
        if calendar is None:
            self.change_calendar(f"You don't have an calendar called {creds.cal_name}; "
                                 f"Please tell me another existing calendar name")
        else:
            return calendar


    def get_events(self, calendar: caldav.objects.Calendar, start: datetime = None, end: datetime = None):
        """Finds all events starting between start and end time from the given calendar object.
        The method also compares the time values of the start and end parameters

		Args:
			calendar: A calendar object where the events are stored.
			start: Optional; A datetime object representing the minimal value for the startdate attribute.
			end: Optional; A datetime object representing the maximum value for the startdate attribute.

		Returns:
			 A list of the events in the given time span.
		"""
        if start is None:
            return calendar.events()
        if start is not None:

            date_events = calendar.date_search(start=start, end=end) # get events between dates
            filtered_events = []

            # compare time sensitive
            for ev in date_events:
                ev_start = ev.instance.vevent.dtstart.value
                # handling date objects, changing them to datetime to allow comparisons
                if not isinstance(ev_start, datetime):
                    ev.instance.vevent.dtstart.value = datetime.combine(ev_start, datetime.min.time())

                if ev.instance.vevent.dtstart.value.astimezone() >= start.astimezone():
                    filtered_events.append(ev)

            if end is not None:
                filtered_events = [i for i in filtered_events if
                                   i.instance.vevent.dtstart.value.astimezone() <= end.astimezone()]
            return filtered_events


    def get_datetime_from_user(self, response_text: str):
        """Gets the input of the user and parses it to a datetime. Repeats itself, if no date can get extracted.

		Args:
			response_text: A string representing the phrase said by Mycroft to ask the user for a date.

		Returns:
		    A datetime object containing the time information contained in the user input.
		"""
        user_input = self.get_response(response_text)
        if user_input is None:
            return self.get_datetime_from_user("Couldnt understand the time stamp. Please try again")

        extracted_datetime = extract_datetime(user_input)
        if extracted_datetime is None:
            return self.get_datetime_from_user("Couldnt understand the time stamp. Please try again")
        else:
            return extracted_datetime[0]


    def modify_event(self, to_edit_event: caldav.objects.Event):
        """Modifies an event object by taking inputs from the user. Asks the user which attributes should get changed
        by which values.

		Args: A event object representing the event object that should be modified.
		"""
        change_att = self.get_response(f"Using appointment {to_edit_event.instance.vevent.summary.value}; "
                                       f"Which attribute do you want to change?")
        if change_att == "start":
            to_edit_event.instance.vevent.dtstart.value = self.get_datetime_from_user("When should it start?")
            to_edit_event.save()
            self.speak(f"Successfully modified your appointment")
        elif change_att == "end":
            to_edit_event.instance.vevent.dtend.value = self.get_datetime_from_user("When should it end?")
            to_edit_event.save()
            self.speak(f"Successfully modified your appointment")
        elif change_att == "name":
            name = self.get_response("How should I call it?")
            to_edit_event.instance.vevent.summary.value = name
            to_edit_event.save()
            self.speak(f"Successfully modified your appointment")
        else:
            self.speak("Sorry I can only modify the start, end and name attribute.")
        again = self.get_response(f"Do you want to change another attribute?")
        if again == "yes":
            self.modify_event(to_edit_event)


    def change_calendar(self, response_text: str, cal_name:str = None):
        """Changes the used calendar from nextcloud on which the actions of the functions are performed
		by changing and saving the cal_name value in the creds file and reimporting it. Reimports the creds file for
		further use in other methods.
		Repeats itself if no calendar object with the given name exists.

		Args:
			response_text: A string representing the phrase said by Mycroft to ask the user for a calendar name.
		"""
        if cal_name is None:
            cal_name = self.get_response(response_text)

        if next((cal for cal in self.get_calendars() if cal.name.lower() == cal_name.lower()), None) is None:
            self.change_calendar(f"You don't have an calendar called {cal_name}; "
                                 f"Please tell me another existing calendar name")
        else:
            creds_file = open("creds.py", "r")
            list_of_lines = creds_file.readlines()
            list_of_lines[3] = f"cal_name = '{cal_name}'"

            creds_file = open("creds.py", "w")
            creds_file.writelines(list_of_lines)
            creds_file.close()
            importlib.reload(creds)
            self.speak(f"Successfully changed to calendar {cal_name}")


    def extract_datetime_from_message(self, message, attribute_name: str, response_text: str):
        """ Extracts an datetime object containing the time info from a given message object. Asks the user for a
        date and time, if the message doesn't contain date an time information.

        Args:
            message: A message object, which could contain datetime information.
            attribute_name: A string representing the name of the data to get from the message object
            response_text: A string containing the phrase mycroft should tell the user to ask for the date

        Returns:
            A datetime object containing the extracted datetime information
        """
        extracted_datetime = message.data.get(attribute_name)
        if extracted_datetime is not None:
            extracted_datetime = extract_datetime(extracted_datetime)[0]
            if extracted_datetime is None:
                extracted_datetime = self.get_datetime_from_user(f"Couldn't understand the date; Please repeat.")
        else:
            extracted_datetime = self.get_datetime_from_user(response_text)
        return extracted_datetime


    def get_name_from_message(self, message, attribute_name: str, name_type: str = 'appointment'):
        """ Extracts data containing a name from a message object. Asks the user for  name if the message doesn't
        contain a name.

        Args:
            message: A message object, which could contain the name information.
            attribute_name: A string representing the name of the data to get from the message object
            name_type: A string containing the name type (e.g. appointment or calendar) to adapt the output text

        Returns:
            A string containing the found name
        """
        name = message.data.get(attribute_name)
        if name is None:
            name = self.get_response(f"What's the name of the {name_type}?")
        return name


    def get_message_from_date(self, date_obj: datetime, with_time: bool =True):
        """ Creates a string that contains the spoken date to add it into a sentence.

        Args:
            date_obj: A datetime object, which should be transformed to a spoken string
            with_time: Boolean to decide, if time values should be added too

        Returns:
            A string containing the spoken date information ( e.g. January 12, 2021 at 19:21)
        """

        date_message = f"{(date_obj).strftime('%B')} {(date_obj).strftime('%d')}, {(date_obj).strftime('%Y')}"
        if with_time:
            date_message = date_message + f" at {(date_obj).strftime('%H:%M')}"
        return date_message


    def search_event_in_list(self, event_list, selected_name: str):
        """ Searches for events in list containing the given name attribute. If multiple matches are found mycroft will
        ask for the start and end attribute to find a single match.

        Args:
            event_list: A list containing event objects which should get filtered
            selected_name: String containing the name to be searched for

        Returns:
            A list containing the event object matching the searched attributes
        """
        event_list = [ev for ev in event_list if ev.instance.vevent.summary.value.lower() == selected_name.lower()]

        # checking if one, none or multiple matches are found and handling the different szenarios
        if len(event_list) == 0:
            self.speak(f"Can't find an appoinment called {selected_name}.")
            return []
        elif len(event_list) == 1:
            return event_list
        elif len(event_list) > 1:
            to_select_start = self.get_datetime_from_user(f"Found multiple appointments called {selected_name};"
                f" Tell me on what date and time the appointment starts, which should be used.").astimezone()
            to_select_events = [ev for ev in event_list if ev.instance.vevent.dtstart.value.astimezone()
                                == to_select_start]
            if len(to_select_events) == 0:
                self.speak(f"Can't find an appointment called {selected_name} at "
                           f"{self.get_message_from_date(to_select_event)}.")
                return []
            elif len(to_select_events) == 1:
                return to_select_events
            else:
                to_select_end = self.get_datetime_from_user(f"Found multiple appointments called {selected_name} "
                    f"starting at the same time; Tell me on what date and time the appointment, which should be used, "
                                                            f"ends.").astimezone()
                to_select_events = [ev for ev in event_list if ev.instance.vevent.dtend.value.astimezone()
                                    == to_select_end]
                if len(to_select_events) == 0:
                    self.speak(f"Can't find an appointment called {selected_name} starting at "
                               f"{self.get_message_from_date(to_select_start)} and ending at "
                               f"{self.get_message_from_date(to_select_end)}.")
                    return []
                elif len(to_select_events) == 1:
                    return to_select_events
                else:
                    self.speak(f"Found multiple events called {selected_name} starting an ending at the same time.")
                    return to_select_events


    @intent_file_handler('change.intent')
    def handle_change(self, message):
        """Changes the used calendar name by callling the change calendar method.
        Gets executed after user inputs, which ask mycroft to change the calendar.
		"""
        cal_name = self.get_name_from_message(message, 'new_name', 'calendar')
        self.change_calendar("Tell me the name of the calendar you want to use", cal_name)


    @intent_file_handler('nextcalendar.intent')
    def handle_nextcalendar(self, message):
        """Informs the User about the next upcoming event(s).
        Gets executed after user inputs, which ask mycroft to inform the user about his next appointment.
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
            if len(next_appointments) > 1:
                first_appointments_string = " ".join(x.instance.vevent.summary.value + ", "
                                                     for x in next_appointments[:-1])

                self.speak(f"You've got multiple next appointments, which are starting at "
                           f"{self.get_message_from_date(start)} and are entitled {first_appointments_string}and "
                           f"{next_appointments[-1].instance.vevent.summary.value}.")
            else:
                output = f"Your next appointment is on {self.get_message_from_date(start)} and is entitled {summary}."
                self.speak(output)


    @intent_file_handler('create.intent')
    def handle_create(self, message):
        """Creates an event with given name, start date and end date. Asks for the attribute values, if they are not
        contained in the message object.
        Gets executed after user inputs, which ask mycroft to create a new appointment.
		"""
        calendar = self.get_calendar()

        # get attributes for new appointment from user
        name = self.get_name_from_message(message, "new_name")

        startdate = self.extract_datetime_from_message(message, 'start_datetime', "When should it start?")\
            .strftime("%Y%m%dT%H%M%S")
        enddate= self.extract_datetime_from_message(message, 'end_datetime', "When should it end?")\
            .strftime("%Y%m%dT%H%M%S")
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


    @intent_file_handler('delete.intent')
    def handle_delete(self, message):
        """Deletes an event with given name. Uses the search event in list to find the correct event by asking for
        more attributes if necessary. If multiple matches are found mycroft asks the user how my should get deleted.
        Gets executed after user inputs, which ask mycroft to delete an appointment.
		"""
        calendar = self.get_calendar()
        future_events = self.get_events(calendar)

        # get the name of the event from message or ask the user if the message doesnt contain the name
        to_delete_name = self.get_name_from_message(message, 'to_delete_name')

        to_delete_events = self.search_event_in_list(future_events, to_delete_name)

        if len(to_delete_events)==1:
            to_delete_events[0].delete()
            self.speak("Successfully deleted the event")
        elif len(to_delete_events)>1:
            del_all = self.get_response("Should I delete all, one or none?")
            if del_all == 'all':
                for ev in to_delete_events:
                    ev.delete()
                self.speak("Okay I deleted all found events")
            elif del_all == 'one':
                to_delete_events[0].delete()
                self.speak("Okay I deleted one of them")
            elif del_all == 'None':
                self.speak("ok, I won't delete any of them.")


    @intent_file_handler("modify.intent")
    def handle_modify(self, message):
        """Modifies an event with given name. Uses the search event in list to find the correct event by asking for
        more attributes if necessary.
		Gets executed after user inputs, which ask mycroft to modify an existing appointment.
		"""
        calendar = self.get_calendar()
        future_events = self.get_events(calendar)

        # asks user for the event name
        to_edit_name = self.get_name_from_message(message, "to_edit_name")

        to_edit_events = self.search_event_in_list(future_events, to_edit_name)

        if len(to_edit_events)==1:
            self.modify_event(to_edit_events[0])
        elif len(to_edit_events)>1:
            self.speak("I will modify one of them. If you want to delete the other one, you can ask me later.")
            self.modify_event(to_edit_events[0])


    @intent_file_handler("getday.intent")
    def handle_getday(self, message):
        """Informs the user of the events on a specific day.
        Gets executed after user inputs, which ask mycroft for appointments on a specific date.
        """
        calendar = self.get_calendar()

        to_get_date = self.extract_datetime_from_message(message, 'date', 'At what day?')

        starttime = to_get_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone()
        endtime = to_get_date.replace(hour=23, minute=59, second=59, microsecond=999).astimezone()

        future_events = self.get_events(calendar, starttime.astimezone(), endtime.astimezone())

        matches = [ev for ev in future_events if ev.instance.vevent.dtstart.value.astimezone().date() ==
                   to_get_date.date()]

        if len(matches) == 0:
            self.speak(f"Couldnt find an appointment at {self.get_message_from_date(to_get_date, False)}.")
        elif len(matches) == 1:
            start = (matches[0].instance.vevent.dtstart.value)
            summary = (matches[0].instance.vevent.summary.value)
            output = f"You've got one appointment on {self.get_message_from_date(start)} and it is entitled {summary}."
            self.speak(output)
        elif len(matches) > 1:
            appointments_string = " ".join(x.instance.vevent.summary.value + ", "
                                           for x in matches[:-1])
            self.speak(f"I've found multiple appointments at {self.get_message_from_date(to_get_date, False)}; They are"
                       f" entitled {appointments_string}and {matches[-1].instance.vevent.summary.value}.")


def create_skill():
    return Nextcalendar()
