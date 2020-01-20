import datetime
import praw
from consts import *
from db import *

class CrossmodDBUpdater:
    def __init__(self):
        self.REMOVED = "[removed]"
        self.DELETED = "[deleted]"

        self.db = CrossmodDB()

        self.session = self.db.database_session

        #setup the Reddit bot
        self.reddit = praw.Reddit(user_agent = CrossmodConsts.REDDIT_USER_AGENT,
                                  client_id = CrossmodConsts.REDDIT_CLIENT_ID, 
                                  client_secret = CrossmodConsts.REDDIT_CLIENT_SECRET,
                                  username = CrossmodConsts.REDDIT_USERNAME, 
                                  password = CrossmodConsts.REDDIT_PASSWORD)

    def update_database_values(self):
        status_count = self.session.query(CrossmodDBUpdateStatus).count()
        if(status_count == 0):
            rows = self.session.query(CrossmodDBData)
        else:
            starting_row_id = self.session.query(CrossmodDBUpdateStatus).order_by(CrossmodDBUpdateStatus.id.desc()).first().last_row_id
            starting_row = self.session.query(CrossmodDBData).filter(CrossmodDBData.id == starting_row_id).first()
            rows = self.session.query(CrossmodDBData).filter(CrossmodDBData.ingested_utc > starting_row.ingested_utc, 
                                                             CrossmodDBData.ingested_utc <= starting_row.ingested_utc + datetime.timedelta(days = 7))
        update_start_utc = datetime.datetime.now()
        rows_updated = 0
        total = rows.count()
        for row in rows:
            if(rows_updated == total - 1):
                last_row_id = row.id
            self.change_moderated_value(row, rows_updated)    
            print("{} rows of {}\r\n".format(rows_updated, total))
            rows_updated += 1
        update_end_utc = datetime.datetime.now()

        if rows_updated > 0:
            status_entry = CrossmodDBUpdateStatus(id = status_count + 1,
                                                update_end_utc = update_end_utc,
                                                rows_updated = rows_updated,
                                                last_row_id = last_row_id)
            self.session.add(status_entry)
            self.session.commit()

    def change_moderated_value(self, row, count):
        comment = self.reddit.comment(id = row.id)

        if comment.banned_at_utc != None and comment.banned_by != None:
            row.banned_by = comment.banned_by
            row.banned_at_utc = datetime.datetime.fromtimestamp(comment.banned_at_utc)

            if count % 20 == 0:
                self.db.database_session.commit()

def main():
    updater = CrossmodDBUpdater()
    updater.update_database_values()

if __name__ == "__main__":
    main()
