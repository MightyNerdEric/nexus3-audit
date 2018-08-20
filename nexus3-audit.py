#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: EPL-1.0
##############################################################################
# Copyright (c) 2018 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v1.0
# which accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v10.html
##############################################################################

import argparse
import csv
import os
import re
import requests

ENV_PASS = "NEXUSPASS"


def get_all_images(session, repo, url_base):
    url = "%s/search?repository=%s" % (url_base, repo)

    # Use global session
    url_attr = session.get(url)
    if url_attr:
        result = url_attr.json()
        items = result["items"]
        cont_token = result["continuationToken"]
    else:
        print url + " returned " + str(url_attr)
        session.close
        exit(1)

    # Check if there are multiple pages of data
    while cont_token:
        continue_url = "%s&continuationToken=%s" % (url, cont_token)
        url_attr = getattr(session, "get")(continue_url)
        result = url_attr.json()
        items += result["items"]
        cont_token = result["continuationToken"]

    return items


def delete_images(session, images_to_delete, url_base):
    for image in images_to_delete:
        url = "%s/components/%s" % (url_base, image["id"])
        print "Deleting %s:%s" % (image["name"], image["version"])
        # Use global session
        url_attr = session.delete(url)
        if url_attr.status_code != 204:
            print url + " returned " + str(url_attr)
            session.close
            exit(1)


def gate_deletion(total_to_delete):
    while True:
        user_input = raw_input("Would you like to delete all "
                               + str(total_to_delete)
                               + " images listed above? [y/N]: ")
        if not user_input or re.search(r"^[nN]", user_input):
            return False
        elif re.search(r"^[yY]", user_input):
            return True


def main():
    # Command line args
    parser = argparse.ArgumentParser(description='Command line parameters')
    parser.add_argument("-u", "--user", dest="user", help="User name for connecting to Nexus")
    parser.add_argument("-p", "--pass", dest="passwd", help="Password for connecting to Nexus")
    parser.add_argument("-y", "--yes", dest="yes", help="Answer 'yes' to all prompts", action="store_true")
    parser.add_argument("--url", dest="url", help="Nexus URL, e.g. \"https://nexus.example.org\"", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--keep", action="store_true", help="Keep images matching the regex argument")
    group.add_argument("--delete", action="store_true", help="Delete images matching the regex argument")
    group.add_argument("--list", action="store_true", help="List matching images")
    parser.add_argument("PATTERN", help="Regex pattern to search for")
    parser.add_argument("REPO", help="Name of the Docker repository in Nexus")

    args = parser.parse_args()

    # If no password was provided in args, check for password environment var
    if not args.passwd and ENV_PASS in os.environ:
        args.passwd = os.environ[ENV_PASS]

    # Process URL
    API_URL_BASE = "https://nexus3.acumos.org/service/siesta/rest/beta"
    if args.url.endswith('/'):
        url_base = args.url + "service/siesta/rest/beta"
    else:
        url_base = args.url + "/service/siesta/rest/beta"

    session = requests.Session()
    session.auth = (str(args.user).strip(), str(args.passwd).strip())

    # Get a list of all images in the repo
    all_images = get_all_images(session, args.REPO, url_base)
    images_to_delete = []
    if args.list:
        included_keys = ["name", "version", "id"]
        count = 0
        with open("audit_list.csv", 'wb') as out_file:
            dw = csv.DictWriter(out_file, fieldnames=included_keys,
                                quoting=csv.QUOTE_ALL)
            dw.writeheader()
            for image in all_images:
                if set(included_keys).issubset(image) \
                   and re.search(args.PATTERN, image["version"]):
                    count += 1
                    print "Name: %s\nVersion: %s\nID: %s\n\n" % (image["name"],
                                                                 image["version"],
                                                                 image["id"])
                    dw.writerow({k:v for k,v in image.iteritems() if
                                 k in included_keys})
        print "Found %s images matching %s in %s" % (count, args.PATTERN,
                                                     args.REPO)
    elif args.keep:
        for image in all_images:
            if set(["name", "version", "id"]).issubset(image) \
               and not re.search(args.PATTERN, image["version"]):
                images_to_delete.append(image)
    elif args.delete:
        for image in all_images:
            if set(["name", "version", "id"]).issubset(image) \
               and re.search(args.PATTERN, image["version"]):
                images_to_delete.append(image)

    if images_to_delete:
        print "The following images will be deleted:"
        for image in images_to_delete:
            print "%s:%s %s" % (image["name"], image["version"], image["id"])
        if args.yes or gate_deletion(len(images_to_delete)):
            delete_images(session, images_to_delete, url_base)

    # close session
    session.close


if __name__ == "__main__":
    main()
