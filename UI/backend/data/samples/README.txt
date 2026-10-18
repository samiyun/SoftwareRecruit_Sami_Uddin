Put image files here (.jpg, .png, .bmp, .gif, .webp).

The sender picks one at random and pushes it to the web app over WebSocket:

    python sender.py

Need a dataset? Search Kaggle (e.g. "butterflies") and drop a folder of images
in here, or point the sender at any folder:

    python sender.py --folder C:/path/to/images
