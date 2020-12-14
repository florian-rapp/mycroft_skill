from mycroft import MycroftSkill, intent_file_handler


class Nextcalendar(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('nextcalendar.intent')
    def handle_nextcalendar(self, message):
        self.speak_dialog('nextcalendar')


def create_skill():
    return Nextcalendar()

