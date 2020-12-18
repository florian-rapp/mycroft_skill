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

		client = caldav.DAVClient(url)
		principal = client.principal()
		calendars = principal.calendars()

		appointments = []
		starts = []

		if len(calendars) > 0:

			for calendar in calendars:
				events = calendar.date_search(datetime.now())
				if(len(events)>0):
					event = events[0]
					event.load()
					e = event.instance.vevent
					appointments.append(e)
					starts.append(e.dtstart.value)

			if(len(starts)==0):
				self.speak("You haven't got an upcoming appointment")
			else:
				earliest = min(starts)
				earliest_appointment = appointments[starts.index(earliest)]

				start = (earliest_appointment.dtstart.value)
				summary = (earliest_appointment.summary.value)
				output = f"Your next appointment is on {(start).strftime('%B')} {(start).strftime('%d')}, {(start).strftime('%y')} at {(start).strftime('%H:%M')} and is entitled {summary}."
				self.speak(output)
		else:
			self.speak("You haven't got an upcoming appointment")


def create_skill():
    return Nextcalendar()

