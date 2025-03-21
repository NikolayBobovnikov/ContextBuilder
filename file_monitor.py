import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileMonitor:
    def __init__(self, callback):
        self.observer = None
        self.callback = callback

    def start(self, files_to_watch):
        if self.observer:
            self.stop()

        self.observer = Observer()
        for file_path in files_to_watch:
            event_handler = self.FileChangeHandler(file_path, self.callback)
            self.observer.schedule(event_handler, os.path.dirname(file_path), recursive=False)
            logging.debug(f"File watcher set for: {file_path}")
        self.observer.start()
        logging.info("File watchers started.")

    def stop(self):
        if self.observer:
            logging.info("Stopping file watchers.")
            self.observer.stop()
            self.observer.join()
            self.observer = None

    class FileChangeHandler(FileSystemEventHandler):
        def __init__(self, file_path, callback):
            self.file_path = file_path
            self.callback = callback

        def on_modified(self, event):
            if event.src_path == self.file_path:
                logging.info(f"Detected modification in {self.file_path}")
                self.callback(self.file_path) 