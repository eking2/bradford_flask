from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_uploads import UploadSet, configure_uploads, patch_request_class
from wtforms import SubmitField, IntegerField
from wtforms.validators import NumberRange
import pandas as pd

from bradford import bradford_calc

app = Flask(__name__)
app.config['SECRET_KEY'] = 'asdfjkasdfja131je2qja9sd0jaas'
app.config['UPLOADED_CSVS_DEST'] = Path(Path.cwd(), 'tmp')
app.config['TMP'] = Path(Path.cwd(), 'tmp')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

csvs = UploadSet(name='csvs', extensions=['csv'])
configure_uploads(app, csvs)

# set max file size
patch_request_class(app)

class UploadForm(FlaskForm):
    csv = FileField('csv', validators=[FileRequired(), FileAllowed(['csv'], 'Upload a CSV file')])
    poly = IntegerField('Polynomial', validators=[NumberRange(1, 5)], default=2)
    submit = SubmitField('Upload')

@app.route('/', methods=['POST', 'GET'])
def home():

    # make folders
    if not app.config['TMP'].exists():
        app.config['TMP'].mkdir()

    # delete leftover files
    to_delete = Path('tmp').iterdir()
    for fn in to_delete:
        fn.unlink()

    form = UploadForm()
    if form.validate_on_submit():

        # flask-upload will automatically call secure_filename
        # saving is not necessary, can read directly into df
        filename = csvs.save(form.csv.data)

        # remove extension, use to name output files
        fn = filename[:-4]
        session['fn'] = fn

        # read df and run bradford calc
        df = pd.read_csv(csvs.path(filename))
        bradford = bradford_calc(df, fn, form.poly.data)
        bradford.run_all()

        return redirect(url_for('results'))
    else:

        return render_template('index.html', form=form)

@app.route('/results')
def results():

    fn = session.pop('fn', None)

    if fn:
        df = pd.read_csv(f'{app.config["TMP"]}/{fn}_concs.csv')
        return render_template('results.html', fn=fn, df=df.to_html(index = False,
            col_space=150,
            justify='left',
            classes=['table-bordered', 'table-striped', 'table-hover']))
    else:
        # prevent users from accessing results without submitting
        return 'No results'

# download the ouput
@app.route('/tmp/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['TMP'], filename, as_attachment=True)


if __name__ == '__main__':

    app.run(debug=True)
