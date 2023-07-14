from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired, URL

class ProductForm(FlaskForm):
    name = StringField("Product name", validators=[DataRequired()])
    description = StringField("Product description")
    img_url = StringField("Image URL", validators=[DataRequired(), URL()])
    vid_url = StringField("Video URL")
    price = FloatField("Price", validators=[DataRequired()])
    tags = StringField("Product Tags")
    designer = StringField("Designer")
    submit = SubmitField('Submit')
