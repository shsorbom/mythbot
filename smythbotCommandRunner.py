from MythTV.services_api import send as api
class smythbot_command(object):
    def __init__(self, raw_command, formatting = True, mythtv_backend = "not set", mythtv_port = 6544):
        self.raw_command = raw_command
        self.formatting = formatting
        self.mythtv_backend = mythtv_backend
        self.mythtv_port = mythtv_port
        self.command_results = [] # A List of dict entries we will be returning to the client
        self.valid_commands = {} # A list of commands we will recognize
    
    async def parse_raw_command(self):
        self.raw_command = self.raw_command.lower()
        self.raw_command = await self.strip_trailing_spaces(self.raw_command)
        command_list = self.raw_command.split("!smythbot ")
        command_list.pop(0) # The zeroeth element in a split list is always blank, therefore useless.
        return command_list
   
    async def strip_trailing_spaces(self, input_string):
        split_input_string = input_string.split()
        list_index = len(split_input_string) - 1
        while split_input_string[list_index] == " " or split_input_string[list_index] == "":
            split_input_string.pop(list_index)
            list_index = list_index - 1
        return " ".join(split_input_string)

    async def poulate_command_index(self):
        command_string_list = await self.parse_raw_command()
        #print("Debug: Length of command string: " + str(len(command_string_list)))
        
        for piece in command_string_list:
            piece = await self.strip_trailing_spaces(piece)
            if piece.startswith("help"):
                self.command_results.append(await self.get_help(piece))
            elif piece.startswith("set mythbackend address"):
                self.command_results.append(await self.set_mythbackend_address(piece))
            elif piece.startswith("set mythbackend port"):
                self.command_results.append(await self.set_mythbackend_port(piece))
            elif piece.startswith("view mythbackend address"):
                self.command_results.append(await self.view_mythbackend_address())
            elif piece.startswith("view mythbackend port"):
                self.command_results.append(await self.view_mythbackend_port())
            elif piece.startswith("display upcoming recordings"):
                self.command_results.append(await self.display_upcoming_recordings())
            #..
            else:
                self.command_results.append(await self.return_error(piece))
        return self.command_results

    async def compiled_command_index(self):
        pass
    
    # Actual bot commands go here: 
    async def get_help(self, help = "help"):
        if help.lower() == "help": 
            help_string = """<h1> Hi, I am sMythbot</h1>
            <p>I exist to manage the MythTv DVR via Matrix chat.</p>
            <p> I currently support the following commands:</p>
            <br><br>
            <strong>!smythbot help:</strong> Display this message <br>
            <strong>!smythbot set mythbackend address:</strong> Sets the mthtv backend address to use for this room.  <br>
            <strong>!smythbot set mythbacked port:</strong> Sets the mthtv backend port to use for this room. <br>
            """
            #<strong></strong>  <br>
        else:
            pass
        command_shard = {"command name":"help", "command output": help_string}
        return command_shard

    async def set_mythbackend_address(self, raw_command_input):
        split_command_string = raw_command_input.split()
        if len(split_command_string) < 4:
            return await self.malformed_command("set mythbackend address", "No Myth Tv Backend address was specified")
        return await self.set_client_property("MythTv Backend Address", split_command_string[3])
    
    async def set_mythbackend_port(self, raw_command_input):
        split_command_string = raw_command_input.split()
        if len(split_command_string) < 4:
            return await self.malformed_command("set mythbackend port", "No Myth Tv Backend port was specified")
        return await self.set_client_property("MythTv Backend Port", split_command_string[3])

    async def view_mythbackend_address(self):
        return await self.view_client_property("MythTv Backend Address", self.mythtv_backend)

    async def view_mythbackend_port(self):
        return await self.view_client_property("MythTv Backend Port", self.mythtv_port)
    
    async def display_upcoming_recordings(self):
        try:
            upcoming_queue = await self._interrogate_mythbackend("Dvr/GetUpcomingList")
        except RuntimeError:
            return await self.connection_error()
        count = int(upcoming_queue['ProgramList']['Count'])
        if count < 1:
            return {"command output": "<h1>No recordiiings are scheduled at ths time</h1>"}
        else:
            style_format = """
            <style>
            table, th, td {
            border: 1px solid black;
            border-collapse: collapse;
            }
            th, td {
            padding: 10px;
            }
            </style>"""
            
            
            schedule_output = """
            <h1>Upcoming Shows</h1>"""
            schedule_output = schedule_output + style_format
            schedule_output = schedule_output +"""<table>
            <tr>
            <th>Series Title</th>
            <th>Episode Title</th>
            <th>Start Time</th>
            <th>End Time</th>
            </tr>
            """
            progs = upcoming_queue['ProgramList']['Programs']
            for program in progs:
                schedule_output = schedule_output + "<tr><td>" + program["Title"] + "</td>"
                schedule_output = schedule_output + "<td>" + program["SubTitle"] + "</td>"
                schedule_output = schedule_output + "<td>" + program["StartTime"] + "</td>"
                schedule_output = schedule_output + "<td>" + program["EndTime"] + "</td>"
            schedule_output = schedule_output + "</table>"
        return{"command output": schedule_output}

    # Internal stuff
    async def return_error(self, bad_string):
        command_shard = {}
        command_shard["command name"] = "command not found"
        command_shard["command output"] = "<h1> The Command: " + bad_string + " was not recognized.</h1><p>Type: <strong>!smythbot help</strong> for more information about currently supported commands.</p>"
        return command_shard
    
    async def connection_error(self):
        error_output = {"command output":"""<h1>There was a problem</h1>
        <p>There was a connection problem when querying your Myth Tv.
        <br>This could mean a few things:
        <ul>
        <li>Your backend URL or port is set incorrectly</li>
        <li>Your Myth Tv backend is down</li>
        <li>Your connection to the Myth Tv is faulty.</li></ul></p>"""}
        return error_output
        
    async def malformed_command(self, command_name, error_reason):
        command_shard = {}
        command_shard["command name"] = "\"" + command_name + "\" was malformed"
        command_shard["command output"] = "<h1>Malformed Command</h1> The command " + command_shard["command name"] +"<p>The reason: " + error_reason + "</p>"
        return command_shard

    async def set_client_property(self, property_name, property_value):
        command_shard = {}
        command_shard["command name"] = "set the " + property_name + " for this room"
        command_shard["room settings data"] = {"property name":property_name, "property value":property_value}
        command_shard["command output"] = "<h1>You " + command_shard["command name"] + " to " + property_value + " </h1>"
        return command_shard

    async def view_client_property(self, property_name, property_value):
        command_shard = {}
        command_shard["command name"] = "The " + property_name + " for this room"
        command_shard["room settings data"] = {"property name":property_name, "property value":property_value}
        command_shard["command output"] = "<h1>" + command_shard["command name"] + " is " + property_value + " </h1>"
        return command_shard
    
    async def _interrogate_mythbackend(self, endpoint_string, command_parameters = ""):
        mythtv_backend_server = api.Send(host=self.mythtv_backend, port=self.mythtv_port)
        try:
            mythtv_response = mythtv_backend_server.send(endpoint=endpoint_string)
        except RuntimeError as e:
            print(e)
            raise  
        return mythtv_response