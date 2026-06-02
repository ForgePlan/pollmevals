# Bug fix: wtforms/wtforms

You are fixing a real bug in the open-source repository `wtforms/wtforms` at commit `848d28d67e45cda7a06c4c8ed2768e6a8cb1c016`.

## Issue

Use HTML 5 widgets
The HTML 5 widgets are kept in their own section and not used by default, but this distinction doesn't make sense today. "HTML 5" is just "HTML" now. No supported browser doesn't understand those input types, and ones that aren't supported fall back to text anyway.

I already sort of started this by making the required validators add the `required` flag, and I'm taking it further with #406 for more complex flags. Fields should default to using the more specific widgets where possible.

Interface / API notes:
Method: Flags.__getattr__(self, name)  
Location: wtforms/fields/core.py → class Flags  
Inputs: *name* – attribute name requested on a Flags instance.  
Outputs: Returns the attribute’s value if it exists; otherwise returns **None** (previously returned False).  
Description: Provides a unified flags object where missing flags evaluate to None, enabling flag‑based widget rendering.

Method: Input.__call__(self, field, **kwargs)  
Location: wtforms/widgets/core.py → class Input  
Inputs: *field* – a WTForms Field instance; **kwargs – optional HTML attributes passed at render time.  
Outputs: A Markup string for an `<input …>` element; automatically injects any flag attributes whose names appear in the widget’s *validation_attrs* list and are set on *field.flags*.  
Description: Renders HTML5‑compatible input elements, pulling validation‑related attributes (e.g., required, minlength, maxlength, min, max, step) from the field’s flags.

Method: TextInput.__call__(self, field, **kwargs) *(inherited, uses Input.__call__)*  
Location: wtforms/widgets/core.py → class TextInput  
Inputs: Same as Input.__call__.  
Outputs: `<input type="text" …>` markup with added validation attributes.  
Description: Text input widget that now supports required, maxlength, minlength, and pattern attributes derived from field flags.

Method: PasswordInput.__call__(self, field, **kwargs)  
Location: wtforms/widgets/core.py → class PasswordInput  
Inputs: Same as Input.__call__.  
Outputs: `<input type="password" …>` markup with validation attributes.  
Description: Password input widget supporting the same validation flags as TextInput.

Method: TextArea.__call__(self, field, **kwargs)  
Location: wtforms/widgets/core.py → class TextArea  
Inputs: *field*; **kwargs.  
Outputs: `<textarea …>` markup with required, maxlength, minlength attributes taken from flags.  
Description: Textarea widget now propagates flag‑based validation attributes.

Method: Select.__call__(self, field, **kwargs)  
Location: wtforms/widgets/core.py → class Select  
Inputs: *field*; **kwargs.  
Outputs: `<select …>` markup with required attribute from flags.  
Description: Select widget now adds a required attribute when the field’s flags indicate it.

Method: SearchField.__init__(self, label=None, validators=None, **kwargs)  
Location: wtforms/fields/core.py → class SearchField (inherits StringField)  
Inputs: *label*, *validators*, additional field kwargs.  
Outputs: Instance of a field rendering `<input type="search">`.  
Description: New convenience field for HTML `search` input type, using the SearchInput widget.

Method: TelField.__init__(self, label=None, validators=None, **kwargs)  
Location: wtforms/fields/core.py → class TelField (inherits StringField)  
Inputs: Same as SearchField.  
Outputs: Instance rendering `<input type="tel">`.  
Description: New field for telephone inputs.

Method: URLField.__init__(self, label=None, validators=None, **kwargs)  
Location: wtforms/fields/core.py → class URLField (inherits StringField)  
Inputs: Same as SearchField.  
Outputs: Instance rendering `<input type="url">`.  
Description: New field for URL inputs.

Method: EmailField.__init__(self, label=None, validators=None, **kwargs)  
Location: wtforms/fields/core.py → class EmailField (inherits StringField)  
Inputs: Same as SearchField.  
Outputs: Instance rendering `<input type="email">`.  
Description: New field for email inputs.

Method: DateTimeLocalField.__init__(self, label=None, validators=None, format="%Y-%m-%d %H:%M:%S", **kwargs)  
Location: wtforms/fields/core.py → class DateTimeLocalField (inherits DateTimeField)  
Inputs: *label*, *validators*, *format*, additional kwargs.  
Outputs: Instance rendering `<input type="datetime-local">`.  
Description: New field for HTML5 datetime‑local inputs.

Method: IntegerRangeField.__init__(self, label=None, validators=None, **kwargs)  
Location: wtforms/fields/core.py → class IntegerRangeField (inherits IntegerField)  
Inputs: Same as IntegerField.  
Outputs: Instance rendering `<input type="range">`.  
Description: New field for numeric range inputs, using the RangeInput widget.

Method: DecimalRangeField.__init__(self, label=None, validators=None, **kwargs)  
Location: wtforms/fields/core.py → class DecimalRangeField (inherits DecimalField)  
Inputs: Same as DecimalField.  
Outputs: Instance rendering `<input type="range">` with step="any".  
Description: New field for decimal range inputs.

Method: Length.__init__(self, min=-1, max=-1, message=None)  
Location: wtforms/validators.py → class Length  
Inputs: *min* (int, default –1), *max* (int, default –1), *message* (optional).  
Outputs: Validator instance with *field_flags* dict containing “minlength” and/or “maxlength” when limits are set.  
Description: Length validator now provides flag information for widget rendering.

Method: NumberRange.__init__(self, min=None, max=None, message=None)  
Location: wtforms/validators.py → class NumberRange  
Inputs: *min* (numeric or None), *max* (numeric or None), *message*.  
Outputs: Validator instance with *field_flags* dict containing “min” and/or “max”.  
Description: NumberRange validator now supplies min/max flags for HTML5 widgets.

Method: Optional.__init__(self, strip_whitespace=True)  
Location: wtforms/validators.py → class Optional  
Inputs: *strip_whitespace* (bool).  
Outputs: Validator instance with *field_flags* = {"optional": True}.  
Description: Optional validator now sets an explicit “optional” flag for widgets.

Method: DataRequired.__init__(self, message=None)  
Location: wtforms/validators.py → class DataRequired  
Inputs: *message* (optional).  
Outputs: Validator instance with *field_flags* = {"required": True}.  
Description: DataRequired now provides a required flag for widget rendering.

Method: InputRequired.__init__(self, message=None)  
Location: wtforms/validators.py → class InputRequired  
Inputs: *message* (optional).  
Outputs: Validator instance with *field_flags* = {"required": True}.  
Description: InputRequired now provides the required flag similarly to DataRequired.

Function: html_params(**kwargs) *(unchanged signature, but now used by widgets to include flag attributes)*  
Location: wtforms/widgets/core.py → helper function.  
Inputs: Arbitrary HTML attribute key/value pairs.  
Outputs: Properly escaped attribute string.  
Description: Generates the attribute list for widget rendering, now receives additional validation attributes from flags.

## Task

Modify the python source so the reported problem is resolved. Produce a patch against the repository at the given base commit that makes the failing tests pass without breaking the existing passing tests.

Constraints:
  - Change only what the fix requires; keep the diff minimal and focused.
  - Do not edit the test files — they are the hidden acceptance criteria.
  - Preserve the existing public API unless the issue explicitly requires a change.

Output a unified diff (git patch) of your source changes.
