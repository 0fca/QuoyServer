from commands.command import Command
from commands.function_set import FunctionSet

class CommandParser():
    @staticmethod
    def parse_command(command_text : str, body_start_index : int = 2) -> list:
        chunks = command_text.rstrip().split(" ")
        parsed_command = []
        if body_start_index != -1:
            for i in range(0, body_start_index):
                parsed_command.append(chunks[i])
            body = ''
            for i in range(body_start_index, len(chunks)):
                body += ' ' + chunks[i]
            parsed_command.append(body.lstrip())
        else:
            parsed_command = chunks
        return parsed_command
    
    @staticmethod
    def find_command(command_text, command_set : list) -> Command:
        command_str = command_text.rstrip().split(" ")[0]
        if command_str in command_set:
            return command_set[command_str]
        else:
            return Command(FunctionSet.on_bad_rqst_hdr, -1)