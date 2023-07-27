from commands.command import Command
from commands.function_set import FunctionSet

class CommandParser():
    '''
    Accepted format for the command is:
    CMD HDR1...HDRn BODY
    Each part of the command is separated by a single space.
    CMD - is a name of command i.e. REG
    HDR - kind of a header, it does not actually holds any values but it can be used as a kind of a switch
    BODY - body of a command
    HDR count is set by the body_start_index parameter, 
        it defaults to 2 and 
        it says that after splitting command (read as a string, not bytes) by space whatever is on 2nd index is taken as a body. 
        Body itself can contain spaces, however it implies that it will be the last part of whole command.
    '''
    @staticmethod
    def parse_command(command_text : str, body_start_index : int = 2) -> list:
        # Split the string of a command by space
        chunks = command_text.rstrip().split(" ")
        parsed_command = []
        # If body_start_index is -1 it means that it has no headers and no body
        if body_start_index != -1:
            # Add command name and all the headers to parsed_command list
            for i in range(0, body_start_index):
                parsed_command.append(chunks[i])
            body = ''
            # Starting from body_start_index, there is a body of a command - concatenate it into one string, chunk by chunk
            for i in range(body_start_index, len(chunks)):
                body += ' ' + chunks[i]
            # Body is now a single string containing spaces, so we can add it as a last segment to parsed command list
            parsed_command.append(body.lstrip())
        else:
            # There is just a name of a command, so chunks equals to resulted parsed command
            parsed_command = chunks
        return parsed_command
    
    '''
    This method tries to find a command name inside command_text variable.
    It bases on commands defined in command_set list, 
    if command_text variable does not contain any command defined in there, find_command will return Command.BAD_RQST_HDR
    '''
    @staticmethod
    def find_command(command_text, command_set : list) -> Command:
        command_str = command_text.rstrip().split(" ")[0]
        if command_str in command_set:
            return command_set[command_str]
        else:
            return Command(FunctionSet.on_bad_rqst_hdr, -1)