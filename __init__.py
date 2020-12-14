from mycroft import MycroftSkill, intent_file_handler
from datetime import datetime, timedelta, time
import caldav
import creds


class Nextcalendar(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('nextcalendar.intent')
    def handle_nextcalendar(self, message):
        url = f"https://{creds.user}:{creds.pw}@next.social-robot.info/nc/remote.php/dav"
        today = datetime.combine(datetime.today(), time(0, 0))

        client = caldav.DAVClient(url)
        principal = client.principal()
        calendars = principal.calendars()

        appointments = []
        starts = []

        if len(calendars) > 0:

            for calendar in calendars:
                events = calendar.date_search(today)
                event = events[0]
                event.load()
                e = event.instance.vevent
                appointments.append(e)
                starts.append(e.dtstart.value)

            earliest = min(starts)
            ind = starts.index(earliest)
            earliest_appointment = appointments[ind]

            try:
                location = earliest_appointment.location.value
            except:
                location = None
            start = (earliest_appointment.dtstart.value)
            summary = (earliest_appointment.summary.value)
            output = f"Your next appointment is on {(start).strftime('%B')} {(start).strftime('%d')}, {(start).strftime('%y')} at {(start).strftime('%H:%m')} and is entitled {summary}."
            self.speak(output)

        else:
            self.speak("You haven't got an upcoming appointment")


def create_skill():
    return Nextcalendar()

