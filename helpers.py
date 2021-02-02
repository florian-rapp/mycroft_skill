from mycroft import MycroftSkill, intent_file_handler
from datetime import datetime, timedelta, time, timezone, date
import caldav
import creds
from mycroft.util.parse import extract_datetime
import importlib


# reads user and password, which are stored in the creds.py file, to access nextcloud (from next.social-robot.info)
# returns a list of all calendars of the user
def get_calendars(self):
    """Gets calendars from CalDav-Url.

    Returns:
        A list of calendars.
    """
    # combining the username, password and nextcloud url (saved in local creds file)
    url = f"https://{creds.user}:{creds.pw}@{creds.url}/nc/remote.php/dav"

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
    calendar = next((cal for cal in calendars if cal.name.lower()
                     == creds.cal_name.lower()), None)
    if calendar is None:
        self.change_calendar(f"You don't have an calendar called {creds.cal_name}. "
                             f"Please tell me another existing calendar name")
    else:
        return calendar


# takes a calendar object as parameter
# optional parameters start and end datime objects, which specify when the event should start
# respects the time values of the start and end parameters
# returns a list of all events (event objects) stored in the calendar, which are lying in the future
def get_events(self, calendar: caldav.objects.Calendar, start: datetime = None, end: datetime = None):
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

        filtered_events = []
        # get events between dates
        # date_events = calendar.date_search(start=start, end=end)
        date_events = calendar.date_search(start=start, end=end)

        # compare time sensitive
        for ev in date_events:
            ev_start = ev.instance.vevent.dtstart.value
            if not isinstance(ev_start, datetime):
                self.speak("changing date to datetime")
                ev.instance.vevent.dtstart.value = datetime.combine(
                    ev_start, datetime.min.time())

            if ev.instance.vevent.dtstart.value.astimezone() >= start.astimezone():
                filtered_events.append(ev)

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
    if user_input is None:
        return self.get_datetime_from_user("Couldnt understand the time stamp. Please try again")

    extracted_datetime = extract_datetime(user_input)
    if extracted_datetime is None:
        return self.get_datetime_from_user("Couldnt understand the time stamp. Please try again")
    else:
        return extracted_datetime[0]


# takes a event object as parameter
# asks the user, which attribute(s) should get changed until the user doesn't want to change anything
# saves the modified event
def modify_event(self, to_edit_event: caldav.objects.Event):
    """modifies an event object.

    Args: A event object representing the modified object.
    """
    change_att = self.get_response(f"Found appointment {to_edit_event.instance.vevent.summary.value}. "
                                   f"Which attribute do you want to change?")
    if change_att == "start":
        # start = self.get_response("When should it start?")
        # to_edit_event.instance.vevent.dtstart.value = extract_datetime(start)[0]
        to_edit_event.instance.vevent.dtstart.value = self.get_datetime_from_user(
            "When should it start?")
        to_edit_event.save()
        self.speak(f"Successfully modified your appointment")
    elif change_att == "end":
        # end = self.get_response("When should it end?")
        # to_edit_event.instance.vevent.dtend.value = extract_datetime(end)[0]
        to_edit_event.instance.vevent.dtend.value = self.get_datetime_from_user(
            "When should it end?")
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
def change_calendar(self, response_text: str, cal_name: str = None):
    """Changes the calendar from nextcloud on which the actions of the functions are performed
    by changing and saving the cal_name value in the creds file and reimporting it.

    Args:
        :param response_text:
            A string representing the phrase said by Mycroft.
        :param cal_name:
            A string representing the name of the calendar.
    """
    if cal_name is None:
        cal_name = self.get_response(response_text)

    if next((cal for cal in self.get_calendars() if cal.name.lower() == cal_name.lower()), None) is None:
        self.change_calendar(f"You don't have an calendar called {cal_name}. "
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


def extract_datetime_from_message(self, message, attribute_name, response_text):
    """Extracts a datetime object from a message string.

    Args:
        :param message:
            A message object.
        :param attribute_name:
            A string representing the name of the attribute variable
        :param response_text:
            A string representing what Mycroft should response if the extracted datetime object is None.

    Returns:
        A datetime object representing the value of the attribute variable.

    """
    extracted_datetime = message.data.get(attribute_name)
    if extracted_datetime is not None:
        extracted_datetime = extract_datetime(extracted_datetime)[0]
        if extracted_datetime is None:
            extracted_datetime = self.get_datetime_from_user(
                f"Couldn't understand the date. Please repeat.")
    else:
        extracted_datetime = self.get_datetime_from_user(response_text)
    return extracted_datetime


def get_name_from_message(self, message, attribute_name: str, name_type: str = 'appointment'):
    """Gets name from a message object.

    Args:
        :param message:
            A message object.
        :param attribute_name:
            A string representing the name of the attribute variable
        :param name_type:
            Optional;
            A string representing of what type the name is.

    Returns:
        A string representing the value of the attribute variable
    """
    name = message.data.get(attribute_name)
    if name is None:
        name = self.get_response(f"What's the name of the {name_type}?")
    return name
