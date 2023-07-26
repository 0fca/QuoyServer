from session_manager import SessionManager
from session_manager import Response
from session_manager import Session

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
        session.wipe_buffer()
        session_manager.halt_session(session.ip())
        return Response("UNREG-OK")
