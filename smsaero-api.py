#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
from datetime import datetime 

major = sys.version_info[0]
minor = sys.version_info[1]

if major == 3:
    if minor > 3:
                print("Python >=3.4 is NOT supported.")
                sys.exit(1)
    try:
        import urllib.request as urlrequest
        from urllib.parse import urlparse, urlencode, urlunparse
    except ImportError as error:
        print("ImportError: {0}".format(error))
        sys.exit(1)

if major == 2:
    try:
        import urllib2 as urlrequest
        from urllib import urlencode
        from urlparse import urlparse, urlunparse
    except ImportError as error:
        print("ImportError: {0}".format(error))
        sys.exit(1)

BASE_URL = "http://gate.smsaero.ru/"

action_params = {"send": {"req": ("user", "password", "to", "text", "from"),
                          "opt": ("from2", "date")},
                 "status": {"req": ("user", "password", "id"), "opt": None},
                 "balance": {"req": ("user", "password"), "opt": None},
                 "senders": {"req": ("user", "password"), "opt": None},
                 "sign": {"req": ("user", "password", "sign"), "opt": None}
                }

SMS_ASCII_LEN = 160
SMS_UTF8_LEN = 70
######################
class APIError(Exception):
    pass

class smsaeroAPI(object):
    def __init__(self, args):
        self.action = args.get("action")
        if self.action is None:
            raise ValueError("Action is not set")
        self._act_build_params(args)

    def _limit_send_text(limit):
        in_ascii = False
        if limit <= 0:
            return

        try:
            self.text.encode('ascii')
        # Message has unicode chars
        except UnicodeDecodeError:
            max_len = 70
            seg_len = 70 - 3
            if getattr(self.text, 'decode', False):
                msg_len = len(self.text.decode('utf-8'))
            else:
                msg_len = len(self.text)
        # All characters of message in ascii
        else: 
            in_ascii = True
            max_len = 160
            seg_len = 160 - 7
            msg_len = len(self.text)
        finally:
            full_segments, text = divmod(max_len, seg_len)

        # Message fit in limit
        if full_segments < limit:
            return
        if full_segments == limit and text == 0:
            return

        # Truncate message
        if in_ascii:
            self.text = self.text[0:limit * seg_len]
        else:
            self.text = unicode(self.text, 'utf-8')[0:limit * seg_len]

        return
    def _act_build_params(self, params):
        q = dict()
        # Check required params
        check = action_params[self.action]
        for field in check["req"]:
            if params[field] is None:
                raise ValueError("Required arg({0}) is not set".format(field))
            else:
                q[field] = params[field]

        # Append optional args if they are set.
        if check["opt"] is not None:
            for field in check["opt"]:
                if params.get(field) is None: continue
                q[field] = params[field]

        # Check limit of messages.
        if self.action == 'send' and params['limit'] is not None:
            self._limit_send_text(params['limit'])

        # Build params to url
        self.querry = urlencode(q)
        del q, params

    def _build_url(self):
        url = urlparse("{0}{1}/?{2}".format(BASE_URL, self.action, self.querry))
        # HACK URL string will cause exception when urlopen() takes url in tuple
        # only strings, only hardcore. parse to tuple then unparse to sting.
        self.url = urlunparse(url)

    def request(self, verbose=False):
        self._build_url()
        try:
            answer = urlrequest.urlopen(self.url)
        except urlrequest.HTTPError as http:
            raise APIError("URL: {0}\nHTTP error: {1}".format(self.url, http))
        except urlrequest.URLError as url_exception:
            raise APIError("urlopen cause exception:", url_exception)

        if answer.info()['content-type'] != "text/plain":
            raise APIError("Wrong Content-Type of API answer: {0}\n"
            "API answer should be in {1}".
            format(answer.info()['content-type'], "text/plain"))

        text = answer.read().decode("utf-8")
        try:
            msg_id, msg_status = text.split('=', 1)
        except ValueError:
            return "{0}".format(text)
        else:
            if verbose:
                return "{0}:{0}".format(msg_id, msg_status)
            else:
                return msg_status

if __name__ == '__main__':
    try:
        import argparse
    except ImportError as error:
        print("{0}: {1}".format("ImportError", error))
        print("  API does not requires argparse module directly.\n"
        "  But, if want use it in CLI, you need install argparse module")
        sys.exit(1)

    def print_help(root_parser):
        class act(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                if values is None:
                    root_parser.parse_args(["--help"])
                root_parser.parse_args([values, "--help"])
        return act
    parser = argparse.ArgumentParser(prog="smsaero-api",
             description="Command line interface for SMS Aero service")

# Not used for now
#    parser.add_argument("-l", "--log",
#                        default="-",
#                        metavar="FILE",
#                        type=argparse.FileType('w'),
#                        help="Write all messages to FILE"
#                        
    default_args = argparse.ArgumentParser(add_help=False)
    default_args.add_argument("-u", "--username",
                              dest="user",
                              required=True,
                              help="SMS-Aero registered username"
                             )
    default_args.add_argument("-p", "--password",
                              required=True,
                              help="SMS-Aero hashed password in md5"
                             )

    # Subparser for API action's
    subparsers = parser.add_subparsers(title="Commands",
                                       metavar="<command>",
                                       dest="action"
                                      )

    # Special subparser that print help of action
    sub = subparsers.add_parser("help", help="Print <command> help",
                                add_help=False)
    sub.add_argument("command", action=print_help(parser),
                     nargs='?', default=None)

    # All other actions.
    sub = subparsers.add_parser("send", help="Send SMS",
                                parents=[default_args])
    sub.add_argument("-r", "--recipient",
                     required=True,
                     dest="to",
                     help="Phone number of recipient"
                    )
    sub.add_argument("-f", "--from",
                     required=True,
                     dest="from",
                     help="Sender Name"
                    )
    sub.add_argument("-g", "--from2",
                     required=False,
                     dest="from2",
                     help="Sender name for Megafon"
                    )
    sub.add_argument("-d", "--date",
                     required=False,
                     help="Date of sending"
                    )
    sub.add_argument("-n" "--send-limit",
                     type=int,
                     required=False,
                     dest="limit",
                     metavar="NUM",
                     help="Setup limit of outgoing sms when text too large." \
                          "Text of message will be truncated"
                    )
    sub.add_argument("text",
                     metavar="MESSAGE",
                     help="Text of message"
                    )
    sub = subparsers.add_parser("status", help="Check SMS status",
                                parents=[default_args])
    sub.add_argument("-i", "--sms-id",
                     required=True,
                     dest="id",
                     help="Internal SMS id"
                    )
    sub = subparsers.add_parser("balance", help="Check balance",
                                parents=[default_args])
    sub = subparsers.add_parser("senders", help="Get senders list",
                                parents=[default_args])
    sub = subparsers.add_parser("sign", help="Create sign",
                                parents=[default_args])
    sub.add_argument("-s" "--sign",
                     required=True,
                     help="Your sign"
                    )
    args = parser.parse_args()
    try:
        args = dict(vars(args))
        sms = smsaeroAPI(args)
    except ValueError as error:
        print("Wrong parametr: {0}".format(error))
        sys.exit(1)
    try:
        print(sms.request())
    except APIError as error:
        print(error)
        sys.exit(1)
    sys.exit(0)
