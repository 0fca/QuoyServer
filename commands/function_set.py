from session_manager import SessionManager
from session_manager import Response
from session_manager import Session
from config import MODULES as mod_conf

import json
import os

'''
This class represents a set of functions which is to be used by a server as a valid set of commands it understands
Methods of this class are mapped to proper command names using Command class objects
'''
class FunctionSet():
    OTP_PROFILE_PATH = "profile:security:otp"

    @staticmethod
    def __parse_bool__(value: str):
        normalized = value.strip().lower()
        if normalized in ("true", "1", "yes", "on", "enabled"):
            return True
        if normalized in ("false", "0", "no", "off", "disabled"):
            return False
        return None

    @staticmethod
    def __read_path__(data: dict, path: str):
        current = data
        for segment in path.split(":"):
            if not isinstance(current, dict) or segment not in current:
                return False, False
            current = current[segment]
        return True, current

    @staticmethod
    def __write_path__(data: dict, path: str, value):
        current = data
        segments = path.split(":")
        for segment in segments[:-1]:
            next_segment = current.get(segment)
            if not isinstance(next_segment, dict):
                next_segment = {}
                current[segment] = next_segment
            current = next_segment
        current[segments[-1]] = value
        return data

    @staticmethod
    def __get_module_ref__(module_refs: dict, module_name: str):
        m = module_refs[module_name]
        mod_instance = getattr(m, "__mod_init__")()
        return mod_instance

    @staticmethod
    def on_hello(args : list, session_manager : SessionManager, opt_args = []) -> Response:
        current_sid = opt_args[1] if len(opt_args) > 1 else None
        current_session = session_manager.existing_session_by_sid(current_sid) if current_sid else None
        if not current_session:
            return Response("BAD-RQST-HDR No active session found")

        session = session_manager.existing_session_by_username(args[0])
        if session and session.sid() != current_session.sid():
            r = Response("IN-USE")
            return r

        current_session.assign_user(args[0])
        if 'persistent_sessions' in mod_conf['ENABLED']:
            session_manager.update_session(current_session.sid())
        return Response("REG-ACK " + args[0] + " " + str(current_session.sid()))

    @staticmethod
    def on_send_ok(args : list,  session_manager : SessionManager, opt_args = []) -> Response:
        session = session_manager.existing_session_by_username(args[0])
        if session:
            r = Response("SEND-OK")
            r2 = Response("DELIVERY %s" % (args[1]))
            session.write_response_for(r2, args[0])
            return r
        else:
            return Response("BAD-RQST-BDY No session found for %s" % args[0])

    @staticmethod
    def on_bad_rqst_hdr(args : list,  session_manager : SessionManager, opt_args = []):
        return Response("BAD-RQST-HDR")

    @staticmethod
    def on_unreg(args : list, session_manager : SessionManager, opt_args = []):
        sid = args[0]
        session : Session = session_manager.existing_session_by_sid(sid)
        if not session:
            return Response("BAD-RQST-HDR invalid sid")
        session_manager.halt_session(session.sid())
        return Response("UNREG-OK")
    
    @staticmethod
    def on_systems_status(args : list, session_manager : SessionManager, opt_args = []):
        # FIXME: This is hardcoded for now, but it should be read from DS - Pika Core API
        systems = {
            'PikaCore': ['core.lukas-bownik.net', 443], 
            'PikaNoteAPI': ['noteapi.lukas-bownik.net', 443], 
            'PikaML': ['ml.lukas-bownik.net', 443],
            'PikaAI': ['ai.lukas-bownik.net', 443],
            'PikaPMR': ['192.168.1.252', 3200]
        }
        system_protocols = {
            'PikaCore': ['TCP', 'HTTP'],
            'PikaNoteAPI': ['TCP'],
            'PikaML': ['TCP'],
            'PikaAI': ['TCP', 'HTTP'],
            'PikaPMR': ['TCP']
        }
        systems_in = args[1].split(",")
        for system_in in systems_in:
            if system_in in system_protocols and system_protocols[system_in]:
                if args[0] == "TCP":
                    m = opt_args[len(opt_args) - 1]['mod_raw_health_check']
                    health_check_func = getattr(m, "conn_check")
                    health_result = health_check_func(systems[system_in][0], systems[system_in][1])
                    return Response(f"SYSSTA={health_result}")
                if args[0] == "HTTP":
                    m = opt_args[len(opt_args) - 1]['mod_http_health_check']
                    health_check_func = getattr(m, "conn_check")
                    health_result = health_check_func(systems[system_in][0], systems[system_in][1])
                    return Response(f"SYSSTA={health_result}")
            else:
                return Response("BAD-RQST-HDR")
            
    @staticmethod
    def on_user_info(args: list, session_manager: SessionManager, opt_args = []):
        module_refs = opt_args[len(opt_args) - 1]
        filter_params = None
        if len(args) >= 2:
            filter_params = args[1]
        if module_refs:
            users = FunctionSet.__get_module_ref__(module_refs, "mod_users")
            sid = args[0]
            session = session_manager.existing_session_by_sid(sid)
            if not session:
                return Response("BAD-RQST-HDR invalid sid")
            user = users.find_by_name(session.username())
            print(user)
            information = user.read_from_data("about_user")
            if filter_params:
                information = information[filter_params]
        else:
            information = {}
        return Response(f".USRNFO={json.dumps(information)}")

    @staticmethod
    def on_user_profile_flag(args: list, session_manager: SessionManager, opt_args = []):
        if len(args) < 2 or not args[0] or not args[1]:
            return Response("BAD-RQST-HDR sid and profile path are required")

        module_refs = opt_args[len(opt_args) - 1]
        users = FunctionSet.__get_module_ref__(module_refs, "mod_users")
        sid = args[0]
        session = session_manager.existing_session_by_sid(sid)
        if not session:
            return Response("BAD-RQST-HDR invalid sid")

        username = session.username()
        expression = args[1].strip()
        chunks = expression.split(" ", 1)
        path = chunks[0].strip()
        if not path:
            return Response("BAD-RQST-HDR profile path is required")
        if path != FunctionSet.OTP_PROFILE_PATH:
            return Response("BAD-RQST-HDR unsupported profile path")

        user = users.find_by_name(username)
        user_data = users.normalize_user_data(user)

        if len(chunks) == 1:
            exists, value = FunctionSet.__read_path__(user_data, path)
            payload = {
                "path": path,
                "exists": exists,
                "value": value if exists else False
            }
            return Response(f".USRPRF={json.dumps(payload)}")

        parsed_value = FunctionSet.__parse_bool__(chunks[1])
        if parsed_value is None:
            return Response("BAD-RQST-HDR value must be true or false")

        updated_data = FunctionSet.__write_path__(user_data, path, parsed_value)
        users.upsert_user_data(username, updated_data)
        payload = {
            "path": path,
            "exists": True,
            "updated": True,
            "value": parsed_value
        }
        return Response(f".USRPRF={json.dumps(payload)}")

    @staticmethod
    def on_dir(args: list, session_manager: SessionManager, opt_args = []):
        module_refs = opt_args[len(opt_args) - 1]
        users = FunctionSet.__get_module_ref__(module_refs, "mod_users")
        sid = args[0]
        subpath = args[1] if args[1] else ""
        if not sid:
            return Response("BAD-RQST-HDR sid is required")
        session = session_manager.existing_session_by_sid(sid)
        if not session:
            return Response("BAD-RQST-HDR invalid sid")
        user_data_dir = users.find_by_name(session.username()).read_from_data("about_user")["data_dir"]
        abs_path = f"{user_data_dir}/{subpath}"
        listing = os.listdir(path=abs_path)
        return Response(f".DIR={json.dumps(listing)}")
    
    @staticmethod
    def on_scrt(args: list, session_manager: SessionManager, opt_args = []):
        module_refs = opt_args[len(opt_args) - 1]
        users = FunctionSet.__get_module_ref__(module_refs, "mod_users")
        sid = args[0]
        path = args[1]
        if not sid:
            return Response("BAD-RQST-HDR sid is required")
        if not path:
            return Response("BAD-RQST-HDR path is required")
        session = session_manager.existing_session_by_sid(sid)
        if not session:
            return Response("BAD-RQST-HDR invalid sid")
        user_data_dir = users.find_by_name(session.username()).read_from_data("about_user")["data_dir"]
        abs_path = f"{user_data_dir}/{path}"
        if os.path.isfile(abs_path):
            with open(abs_path, mode="r+") as fh:
                content = fh.read().strip()
                return Response(f".S.CRT={content}")

    @staticmethod
    def on_sdkr(args: list, session_manager: SessionManager, opt_args = []):
        if not args[0]:
            return Response("BAD-RQST-HDR This command requires at least container name")
        name = args[0]
        flags = []
        if len(args) > 2:
            flags = args[1].split(" ")
    
        module_refs = opt_args[len(opt_args) - 1]
        docker_stats = FunctionSet.__get_module_ref__(module_refs, "mod_docker_stats")
        return Response(f".S.DKR={docker_stats.container_status(name, False)}")
