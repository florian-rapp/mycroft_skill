from mycroft import MycroftSkill, intent_file_handler
from datetime import datetime, timedelta, time, timezone
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

		# get calendar according to the selected calendar name
		calendar = next((cal for cal in calendars if cal.name == creds.cal_name), None)

		# get list of all upcoming events
		future_events = calendar.date_search(start=datetime.now())
		future_events = [i for i in future_events if
						 i.instance.vevent.dtstart.value > datetime.now(timezone.utc).astimezone()]

		if (len(future_events) == 0):
			self.speak("You haven't got an upcoming appointment")
		else:
			# sort events by their start date
			future_events.sort(key=lambda x: x.instance.vevent.dtstart.value)
			next_appointment = future_events[0].instance.vevent

			start = (next_appointment.dtstart.value)
			summary = (next_appointment.summary.value)

			output = f"Your next appointment is on {(start).strftime('%B')} {(start).strftime('%d')}, {(start).strftime('%y')} at {(start).strftime('%H:%M')} and is entitled {summary}."
			self.speak(output)


def create_skill():
    return Nextcalendar()

