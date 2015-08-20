#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yuki Furuta <furushchev@jsk.imi.i.u-tokyo.ac.jp>


import tornado.ioloop
import tornado.web
import motor
from motor import gen
import os

import rospy
import mongodb_store.util as ms_util

import numpy as np
import cv2

image_path = os.path.join("/tmp", "ros_mongo_viewer", "image")
rows_per_page = 100

def prettyprint(d, indent=0, linesep="<br/>", tab="&nbsp;&nbsp;"):
    if not isinstance(d, dict):
        return d
    ret = ""
    for k,v in d.iteritems():
        ret += tab * indent + str(k)
        if isinstance(v, dict):
            ret += linesep + prettyprint(v, indent+1)
        else:
            ret += ": " + str(v) + linesep
    return ret
    

class DOTDict(dict):
    def __getattr__(self, attr):
        o = self.get(attr)
        if isinstance(o, dict):
            return DotDict(o)
        else: return o
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    def getByDot(self, attr):
        val = self
        try:
            for a in  attr.split("."):
                val = val.get(a)
            return prettyprint(val)
        except: return "N/A"

class CompressedImageDict(DOTDict):
    def get(self, attr):
        if (self["_meta"]["stored_type"] == "sensor_msgs/CompressedImage") and attr is "data":
            save_path = os.path.join(image_path, "%s.jpg" % self["_id"])
            if not os.path.exists(save_path):
                self.createImage(save_path)
            path = '<img src="%s" height="100">' % os.path.join("image", "%s.jpg" % self["_id"])
            return path
        else:
            return super(CompressedImageDict, self).get(attr)

    def createImage(self, save_path):
        print "createImage:", save_path
        np_arr = np.fromstring(super(CompressedImageDict, self).get("data"), np.uint8)
        img = cv2.imdecode(np_arr, cv2.CV_LOAD_IMAGE_COLOR)
        if not cv2.imwrite(save_path, img):
            raise "Cannot create image"

class ROSDict(CompressedImageDict):
    def get(self, attr):
        return super(ROSDict, self).get(attr)

class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        page = self.get_query_argument("p", default="0")
        msg_type = self.get_query_argument("type",default=None)
        db = self.settings['db']

        cur = db.pr1012
        if msg_type:
            cur = cur.find({"_meta.stored_type": msg_type})
        else:
            cur = cur.find()
        cur = cur.sort([('$natural',-1)])
        total = yield cur.count()
        print "total", total
        total_page = total / rows_per_page + 1

        page = int(page)
        if page >= total_page:
            page = total_page - 1
        print "page", page
        cur = cur.skip(rows_per_page * page)
        results = yield cur.to_list(rows_per_page) #, callback=self._render)
        self.render("index.html",
                    title="ROS Mongo Viewer",
                    css_files=[],
                    js_files=[],
                    total_page=total_page,
                    current_page=page,
                    labels=["_meta.inserted_at",
                            "_meta.stored_type",
                            "header.frame_id",
                            "transform",
                             # "format",
                              "data"],
                    results=[ROSDict(r) for r in results],
                    )

def createApp():
    if not os.path.exists(image_path):
        os.makedirs(image_path)
    app = tornado.web.Application([
        (r"/", IndexHandler),
        (r"/image/(.*)$", tornado.web.StaticFileHandler, {"path": image_path}),
    ],
    template_path=os.path.join(os.getcwd(), "view"),
    static_path=os.path.join(os.getcwd(), "public"),
    db=motor.MotorClient().jsk_robot_lifelog,
    )
    return app

if __name__ == '__main__':
    app = createApp()
    app.listen(3000)
    tornado.ioloop.IOLoop.instance().start()
