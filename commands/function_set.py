from session_manager import SessionManager
from session_manager import Response
from session_manager import Session
from config import MODULES as mod_conf

'''
This class represents a set of functions which is to be used by a server as a valid set of commands it understands
Methods of this class are mapped to proper command names using Command class objects
'''
class FunctionSet():
    @staticmethod
    def on_hello(args : list, session_manager : SessionManager, opt_args = []) -> Response:
        session = session_manager.existing_session_by_username(args[0])
        if session:
            r = Response("IN-USE")
            return r
        session : Session = session_manager.existing_session_by_ip(opt_args[0])
        if session:
            r = Response("REG-ACK " + args[0] + " " + str(session.sid()))
            session.assign_user(args[0])
            if 'persistent_sessions' in mod_conf['ENABLED']:
                session_manager.update_session(session.sid())
            return r
        else:
            return None

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
        session_manager.halt_session(session.ip())
        return None
    
    @staticmethod
    def on_systems_status(args : list, session_manager : SessionManager, opt_args = []):
        # FIXME: This is hardcoded for now, but it should be read from DS - Pika Core API
        systems = {
            'PikaCore': ['core.lukas-bownik.net', 443], 
            'PikaNoteAPI': ['note.lukas-bownik.net', 443], 
            'PikaML': ['ml.lukas-bownik.net', 443]
        }
        system_protocols = {
            'PikaCore': ['TCP', 'HTTP'],
            'PikaNoteAPI': ['TCP'],
            'PikaML': ['TCP']
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

