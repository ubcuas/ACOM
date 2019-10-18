import xmltodict
import os 

# A class that parses the Mavlink messages definitions
# Source: https://raw.githubusercontent.com/mavlink/mavlink/master/message_definitions/v1.0/common.xml
class MavlinkMessage:
    mavlink_messages = {}

    def __init__(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        project_path = os.path.dirname(dir_path)
        with open(os.path.join(project_path, 'resources/mavlink_messages_v1.0.xml'), 'r') as fd:
            self.mavlink_messages = xmltodict.parse(fd.read())

    # returns the attributes of the message of interest
    # Example: get_message_attr('GPS_RAW_INT') -> ['time_usec', 'fix_type', 'lat', 'lon', 'alt' ...]
    def get_message_attrs(self, message_name):
        messages = self.mavlink_messages['mavlink']['messages']['message']
        result_list = []
        # iterate through the messages tree
        for message in messages:
            if message['@name'] == message_name:
                # iterate through the fields to retrieve attributes
                for field in message['field']:
                    result_list.append(field['@name'])

        return result_list