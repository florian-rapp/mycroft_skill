from mycroft import MycroftSkill, intent_file_handler
from datetime import datetime, timedelta, time, timezone, date
import caldav
import creds
from mycroft.util.parse import extract_datetime
import importlib
import helpers


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

    # gets executed after user inputs, which asks mycroft to change the calendar
    # calls change_calendar method to change the used calendar
    @intent_file_handler('change.intent')
    def handle_change(self, message):
        """Handles the change an event skill.
                """
        cal_name = self.get_name_from_message(message, 'new_name', 'calendar')
        helpers.change_calendar(
            "Tell me the name of the calendar you want to use", cal_name)

    # gets executed after user inputs, which asks mycroft to inform the user about his next appointment
    @intent_file_handler('nextcalendar.intent')
    def handle_nextcalendar(self, message):
        """Informs the User about the next upcoming event.
                """
        calendar = helpers.get_calendar()

        # get list of all upcoming events
        future_events = helpers.get_events(
            calendar, datetime.now().astimezone())

        if (len(future_events) == 0):
            self.speak("You haven't got an upcoming appointment")
        else:
            # sort events by their start date
            future_events.sort(
                key=lambda x: x.instance.vevent.dtstart.value.astimezone())

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
                           f"{(start).strftime('%B')} {(start).strftime('%d')}, {(start).strftime('%Y')} at "
                           f"{(start).strftime('%H:%M')} and are entitled {first_appointments_string}and "
                           f"{next_appointments[-1].instance.vevent.summary.value}.")
            else:
                output = f"Your next appointment is on {(start).strftime('%B')} {(start).strftime('%d')}, " \
                         f"{(start).strftime('%Y')} at {(start).strftime('%H:%M')} and is entitled {summary}."
                self.speak(output)

    # gets executed after user inputs, which asks mycroft to create a new appointment
    @intent_file_handler('create.intent')
    def handle_create(self, message):
        """Creates an event with given name, start date and end date.
                """

        calendar = helpers.get_calendar()

        # get attributes for new appointment from user
        name = helpers.get_name_from_message(message, "new_name")

        startdate = helpers.extract_datetime_from_message(message, 'start_datetime', "When should it start?") \
            .strftime("%Y%m%dT%H%M%S")

        enddate = helpers.extract_datetime_from_message(message, 'end_datetime', "When should it end?") \
            .strftime("%Y%m%dT%H%M%S")
        # enddate = self.get_datetime_from_user("When should it end").strftime("%Y%m%dT%H%M%S")

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
        calendar = helpers.get_calendar()
        future_events = helpers.get_events(calendar)

        # ask the user for the name of the event
        to_delete_name = helpers.get_name_from_message(
            message, 'to_delete_name')

        # get list for all upcoming events with the specified name
        matches = [ev for ev in future_events if ev.instance.vevent.summary.value.lower(
        ) == to_delete_name.lower()]

        # checking if one, none or multiple matches are found and handling the different szenarios
        if len(matches) == 0:
            self.speak(f"Can't find an appoinment called {to_delete_name}")
        elif len(matches) > 1:
            to_delete_date = helpers.get_datetime_from_user(f"found multiple appointments called "
                                                            f"{to_delete_name}. Tell me on what date and time it should"
                                                            f" get deleted.").astimezone()
            to_delete_event = [
                ev for ev in matches if ev.instance.vevent.dtstart.value.astimezone() == to_delete_date]
            if len(to_delete_event) == 0:
                self.speak(
                    f"Can't find an appointment called {to_delete_name} at {to_delete_date}.")
            else:
                to_delete_event[0].delete()
                self.speak(
                    f"Succesfully deleted the appointment {to_delete_name}")
        elif len(matches) == 1:
            matches[0].delete()
            self.speak(f"Succesfully deleted the appointment {to_delete_name}")

    # gets executed after user inputs, which asks mycroft to modify an existing appointment
    @intent_file_handler("modify.intent")
    def handle_modify(self, message):
        """Modifies an event with given name. If more than one event exists with the given name the date /
        will be added to the filter.
                """

        calendar = helpers.get_calendar()
        future_events = helpers.get_events(calendar)

        # asks user for the event name
        to_edit_name = helpers.get_name_from_message(message, "to_edit_name")

        # get list of events with the specified name
        matches = [ev for ev in future_events if ev.instance.vevent.summary.value.lower(
        ) == to_edit_name.lower()]

        # checking if one, none or multiple matches are found and handling the different szenarios
        if len(matches) == 0:
            to_edit_event = None
            self.speak(f"Can't find an appoinment called {to_edit_name}")
        elif len(matches) > 1:
            to_edit_date = helpers.get_datetime_from_user(f"found multiple appointments called "
                                                          f"{to_edit_name}. Tell me on what date and time it should "
                                                          f"get modified.").astimezone()
            to_edit_event = [
                ev for ev in matches if ev.instance.vevent.dtstart.value.astimezone() == to_edit_date]
            if len(to_edit_event) == 0:
                self.speak(
                    f"Couldnt find an appointment called {to_edit_name} at {to_edit_date}.")
                to_edit_event = None
            else:
                to_edit_event = to_edit_event[0]
        elif len(matches) == 1:
            to_edit_event = matches[0]

        # checking if a match was found and calling the modify_event method to change the events attributes
        if type(to_edit_event) == caldav.objects.Event:
            helpers.modify_event(to_edit_event)

    @intent_file_handler("getday.intent")
    def handle_getday(self, message):
        """Informs the user of the events on a specific day.
        """
        calendar = helpers.get_calendar()

        to_get_date = None

        # # extracted_datetime = extract_datetime(message.data.get('date'))[0]
        # if message.data.get('date') is None:
        #     to_get_date = self.get_datetime_from_user("Couldnt understand the time stamp. Please try again")
        # else:
        #     # to_get_date = extract_datetime
        #     to_get_date = extract_datetime(message.data.get('date'))[0]
        #     # todo: check if None
        to_get_date = helpers.extract_datetime_from_message(
            message, 'date', 'At what day?')

        starttime = to_get_date.replace(
            hour=0, minute=0, second=0, microsecond=0).astimezone()

        endtime = to_get_date.replace(
            hour=23, minute=59, second=59, microsecond=999).astimezone()

        future_events = helpers.get_events(
            calendar, starttime.astimezone(), endtime.astimezone())

        matches = [ev for ev in future_events if ev.instance.vevent.dtstart.value.astimezone().date() ==
                   to_get_date.date()]

        if len(matches) == 0:
            self.speak(f"Couldnt find an appointment at {to_get_date.strftime('%B')} {to_get_date.strftime('%d')} "
                       f"{to_get_date.strftime('%Y')}.")
        elif len(matches) == 1:
            # self.speak(f"I've found one appointment at {to_edit_date}.")
            start = (matches[0].instance.vevent.dtstart.value)
            summary = (matches[0].instance.vevent.summary.value)
            output = f"You've got one appointment on {(start).strftime('%B')} {(start).strftime('%d')}, " \
                     f"{(start).strftime('%Y')} at {(start).strftime('%H:%M')} and it is entitled {summary}."
            self.speak(output)
        elif len(matches) > 1:
            appointments_string = " ".join(x.instance.vevent.summary.value + ", "
                                           for x in matches[:-1])
            self.speak(f"I've found more than one appointment at {to_get_date.strftime('%B')} "
                       f"{to_get_date.strftime('%d')} {(to_get_date).strftime('%Y')}. They are entitled "
                       f"{appointments_string}and {matches[-1].instance.vevent.summary.value}.")


def create_skill():
    return Nextcalendar()
