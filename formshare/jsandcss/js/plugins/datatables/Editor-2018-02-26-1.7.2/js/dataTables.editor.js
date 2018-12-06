/*! DataTables Editor v1.7.2
 *
 * ©2012-2018 SpryMedia Ltd, all rights reserved.
 * License: editor.datatables.net/license
 */

/**
 * @summary     DataTables Editor
 * @description Table editing library for DataTables
 * @version     1.7.2
 * @file        dataTables.editor.js
 * @author      SpryMedia Ltd
 * @contact     www.datatables.net/contact
 */

/*jslint evil: true, undef: true, browser: true */
/*globals jQuery,alert,console */

(function( factory ){
	if ( typeof define === 'function' && define.amd ) {
		// AMD
		define( ['jquery', 'datatables.net'], function ( $ ) {
			return factory( $, window, document );
		} );
	}
	else if ( typeof exports === 'object' ) {
		// CommonJS
		module.exports = function (root, $) {
			if ( ! root ) {
				root = window;
			}

			if ( ! $ || ! $.fn.dataTable ) {
				$ = require('datatables.net')(root, $).$;
			}

			return factory( $, root, root.document );
		};
	}
	else {
		// Browser
		factory( jQuery, window, document );
	}
}(function( $, window, document, undefined ) {
'use strict';
var DataTable = $.fn.dataTable;


if ( ! DataTable || ! DataTable.versionCheck || ! DataTable.versionCheck('1.10.7') ) {
	throw 'Editor requires DataTables 1.10.7 or newer';
}

/**
 * Editor is a plug-in for <a href="http://datatables.net">DataTables</a> which
 * provides an interface for creating, reading, editing and deleting and entries
 * (a CRUD interface) in a DataTable. The documentation presented here is
 * primarily focused on presenting the API for Editor. For a full list of
 * features, examples and the server interface protocol, please refer to the <a
 * href="http://editor.datatables.net">Editor web-site</a>.
 *
 * Note that in this documentation, for brevity, the `DataTable` refers to the
 * jQuery parameter `jQuery.fn.dataTable` through which it may be  accessed.
 * Therefore, when creating a new Editor instance, use `jQuery.fn.Editor` as
 * shown in the examples below.
 *
 *  @class
 *  @param {object} [oInit={}] Configuration object for Editor. Options
 *    are defined by {@link Editor.defaults}.
 *  @requires jQuery 1.7+
 *  @requires DataTables 1.10+
 */
var Editor = function ( opts )
{
	if ( ! (this instanceof Editor) ) {
		alert( "DataTables Editor must be initialised as a 'new' instance'" );
	}

	this._constructor( opts );
};

// Export Editor as a DataTables property
DataTable.Editor = Editor;
$.fn.DataTable.Editor = Editor;

// Internal methods


/**
 * Get an Editor node based on the data-dte-e (element) attribute and return it
 * as a jQuery object.
 *  @param {string} dis The data-dte-e attribute name to match for the element
 *  @param {node} [ctx=document] The context for the search - recommended this
 *    parameter is included for performance.
 *  @returns {jQuery} jQuery object of found node(s).
 *  @private
 */
var _editor_el = function ( dis, ctx )
{
	if ( ctx === undefined ) {
		ctx = document;
	}

	return $('*[data-dte-e="'+dis+'"]', ctx);
};


/** @internal Counter for unique event namespaces in the inline control */
var __inlineCounter = 0;

var _pluck = function ( a, prop )
{
	var out = [];

	$.each( a, function ( idx, el ) {
		out.push( el[ prop ] );
	} );

	return out;
};

// The file and file methods are common on both the DataTables and Editor APIs
// so rather than writing the same methods twice, they are defined once here and
// assigned as required.
var _api_file = function ( name, id )
{
	var table = this.files( name ); // can throw. `this` will be Editor or
	var file = table[ id ];         //  DataTables.Api context. Both work.

	if ( ! file ) {
		throw 'Unknown file id '+ id +' in table '+ name;
	}

	return table[ id ];
};

var _api_files = function ( name )
{
	if ( ! name ) {
		return Editor.files;
	}

	var table = Editor.files[ name ];

	if ( ! table ) {
		throw 'Unknown file table name: '+ name;
	}

	return table;
};

/**
 * Get the keys of an object / array
 *
 * @param  {object} o Object to get the keys of
 * @return {array} Keys
 */
var _objectKeys = function ( o ) {
	var out = [];

	for ( var key in o ) {
		if ( o.hasOwnProperty( key ) ) {
			out.push( key );
		}
	}

	return out;
};

/**
 * Compare parameters for difference - diving into arrays and objects if
 * needed, allowing the object reference to be different, but the contents to
 * match.
 *
 * Please note that LOOSE type checking is used
 *
 * @param  {*} o1 Object to compare
 * @param  {*} o2 Object to compare
 * @return {boolean} `true` if matching, `false` otherwise
 */
var _deepCompare = function (o1, o2) {
	if ( typeof o1 !== 'object' || typeof o2 !== 'object' ) {
		return o1 == o2;
	}

	var o1Props = _objectKeys( o1 );
	var o2Props = _objectKeys( o2 );

	if (o1Props.length !== o2Props.length) {
		return false;
	}

	for ( var i=0, ien=o1Props.length ; i<ien ; i++ ) {
		var propName = o1Props[i];

		if ( typeof o1[propName] === 'object' ) {
			if ( ! _deepCompare( o1[propName], o2[propName] ) ) {
				return false;
			}
		}
		else if (o1[propName] != o2[propName]) {
			return false;
		}
	}

	return true;
};

// Field class


Editor.Field = function ( opts, classes, host ) {
	var that = this;
	var multiI18n = host.i18n.multi;

	opts = $.extend( true, {}, Editor.Field.defaults, opts );
	
	if ( ! Editor.fieldTypes[ opts.type ] ) {
		throw "Error adding field - unknown field type "+opts.type;
	}

	this.s = $.extend( {}, Editor.Field.settings, { // has to be a shallow copy!
		type:       Editor.fieldTypes[ opts.type ],
		name:       opts.name,
		classes:    classes,
		host:       host,
		opts:       opts,
		multiValue: false
	} );

	// No id, so assign one to have the label reference work
	if ( ! opts.id ) {
		opts.id = 'DTE_Field_'+opts.name;
	}

	// Backwards compatibility
	if ( opts.dataProp ) {
		opts.data = opts.dataProp;
	}

	// If no `data` option is given, then we use the name from the field as the
	// data prop to read data for the field from DataTables
	if ( opts.data === '' ) {
		opts.data = opts.name;
	}

	// Get and set functions in the data object for the record
	var dtPrivateApi = DataTable.ext.oApi;
	this.valFromData = function ( d ) { // get val from data
		// wrapper to automatically pass `editor` as the type
		return dtPrivateApi._fnGetObjectDataFn( opts.data )( d, 'editor' );
	};
	this.valToData = dtPrivateApi._fnSetObjectDataFn( opts.data ); // set val to data

	// Field HTML structure
	var template = $(
		'<div class="'+classes.wrapper+' '+classes.typePrefix+opts.type+' '+classes.namePrefix+opts.name+' '+opts.className+'">'+
			'<label data-dte-e="label" class="'+classes.label+'" for="'+Editor.safeId(opts.id)+'">'+
				opts.label+
				'<div data-dte-e="msg-label" class="'+classes['msg-label']+'">'+opts.labelInfo+'</div>'+
			'</label>'+
			'<div data-dte-e="input" class="'+classes.input+'">'+
				// Field specific HTML is added here if there is any
				'<div data-dte-e="input-control" class="'+classes.inputControl+'"/>'+
				'<div data-dte-e="multi-value" class="'+classes.multiValue+'">'+
					multiI18n.title+
					'<span data-dte-e="multi-info" class="'+classes.multiInfo+'">'+
						multiI18n.info+
					'</span>'+
				'</div>'+
				'<div data-dte-e="msg-multi" class="'+classes.multiRestore+'">'+
					multiI18n.restore+
				'</div>'+
				'<div data-dte-e="msg-error" class="'+classes['msg-error']+'"></div>'+
				'<div data-dte-e="msg-message" class="'+classes['msg-message']+'">'+opts.message+'</div>'+
				'<div data-dte-e="msg-info" class="'+classes['msg-info']+'">'+opts.fieldInfo+'</div>'+
			'</div>'+
		'</div>');

	var input = this._typeFn( 'create', opts );
	if ( input !== null ) {
		_editor_el('input-control', template).prepend( input );
	}
	else {
		template.css('display', "none");
	}

	this.dom = $.extend( true, {}, Editor.Field.models.dom, {
		container:    template,
		inputControl: _editor_el('input-control', template),
		label:        _editor_el('label', template),
		fieldInfo:    _editor_el('msg-info', template),
		labelInfo:    _editor_el('msg-label', template),
		fieldError:   _editor_el('msg-error', template),
		fieldMessage: _editor_el('msg-message', template),
		multi:        _editor_el('multi-value', template),
		multiReturn:  _editor_el('msg-multi', template),
		multiInfo:    _editor_el('multi-info', template)
	} );

	// On click - set a common value for the field
	this.dom.multi.on( 'click', function () {
		if ( that.s.opts.multiEditable && ! template.hasClass( classes.disabled ) && opts.type !== 'readonly' ) {
			that.val('');
		}
	} );

	this.dom.multiReturn.on( 'click', function () {
		that.multiRestore();
	} );

	// Field type extension methods - add a method to the field for the public
	// methods that each field type defines beyond the default ones that already
	// exist as part of this instance
	$.each( this.s.type, function ( name, fn ) {
		if ( typeof fn === 'function' && that[name] === undefined ) {
			that[ name ] = function () {
				var args = Array.prototype.slice.call( arguments );

				args.unshift( name );
				var ret = that._typeFn.apply( that, args );

				// Return the given value if there is one, or the field instance
				// for chaining if there is no value
				return ret === undefined ?
					that :
					ret;
			};
		}
	} );
};


Editor.Field.prototype = {
	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Public
	 */
	def: function ( set ) {
		var opts = this.s.opts;

		if ( set === undefined ) {
			// Backwards compat
			var def = opts['default'] !== undefined ?
				opts['default'] :
				opts.def;

			return $.isFunction( def ) ?
				def() :
				def;
		}

		opts.def = set;
		return this;
	},

	disable: function () {
		this.dom.container.addClass( this.s.classes.disabled );

		this._typeFn( 'disable' );

		return this;
	},

	displayed: function () {
		var container = this.dom.container;

		return container.parents('body').length && container.css('display') != 'none' ?
			true :
			false;
	},

	enable: function () {
		this.dom.container.removeClass( this.s.classes.disabled );

		this._typeFn( 'enable' );

		return this;
	},

	enabled: function () {
		return this.dom.container.hasClass( this.s.classes.disabled ) === false;
	},

	error: function ( msg, fn ) {
		var classes = this.s.classes;

		// Add or remove the error class
		if ( msg ) {
			this.dom.container.addClass( classes.error );
		}
		else {
			this.dom.container.removeClass( classes.error );
		}

		this._typeFn( 'errorMessage', msg );

		return this._msg( this.dom.fieldError, msg, fn );
	},

	fieldInfo: function ( msg ) {
		return this._msg( this.dom.fieldInfo, msg );
	},

	isMultiValue: function () {
		return this.s.multiValue && this.s.multiIds.length !== 1;
	},

	inError: function () {
		return this.dom.container.hasClass( this.s.classes.error );
	},

	input: function () {
		return this.s.type.input ?
			this._typeFn( 'input' ) :
			$('input, select, textarea', this.dom.container);
	},

	focus: function () {
		if ( this.s.type.focus ) {
			this._typeFn( 'focus' );
		}
		else {
			$('input, select, textarea', this.dom.container).focus();
		}

		return this;
	},

	get: function () {
		// When multi-value a single get is undefined
		if ( this.isMultiValue() ) {
			return undefined;
		}

		var val = this._typeFn( 'get' );
		return val !== undefined ?
			val :
			this.def();
	},

	hide: function ( animate ) {
		var el = this.dom.container;

		if ( animate === undefined ) {
			animate = true;
		}

		if ( this.s.host.display() && animate ) {
			el.slideUp();
		}
		else {
			el.css( 'display', 'none' );
		}
		return this;
	},

	label: function ( str ) {
		var label = this.dom.label;
		var labelInfo = this.dom.labelInfo.detach();

		if ( str === undefined ) {
			return label.html();
		}

		label.html( str );
		label.append( labelInfo );
		return this;
	},

	labelInfo: function ( msg ) {
		return this._msg( this.dom.labelInfo, msg );
	},

	message: function ( msg, fn ) {
		return this._msg( this.dom.fieldMessage, msg, fn );
	},

	// There is no `multiVal()` as its arguments could be ambiguous
	// id is an idSrc value _only_
	multiGet: function ( id ) {
		var value;
		var multiValues = this.s.multiValues;
		var multiIds = this.s.multiIds;

		if ( id === undefined ) {
			// Get an object with the values for each item being edited
			value = {};

			for ( var i=0 ; i<multiIds.length ; i++ ) {
				value[ multiIds[i] ] = this.isMultiValue() ?
					multiValues[ multiIds[i] ] :
					this.val();
			}
		}
		else if ( this.isMultiValue() ) {
			// Individual value
			value = multiValues[ id ];
		}
		else {
			// Common value
			value = this.val();
		}

		return value;
	},
	
	multiRestore: function () {
		this.s.multiValue = true;
		this._multiValueCheck();
	},

	multiSet: function ( id, val )
	{
		var multiValues = this.s.multiValues;
		var multiIds = this.s.multiIds;

		if ( val === undefined ) {
			val = id;
			id = undefined;
		}

		// Set
		var set = function ( idSrc, val ) {
			// Get an individual item's value - add the id to the edit ids if
			// it isn't already in the set.
			if ( $.inArray( multiIds ) === -1 ) {
				multiIds.push( idSrc );
			}

			multiValues[ idSrc ] = val;
		};

		if ( $.isPlainObject( val ) && id === undefined ) {
			// idSrc / value pairs passed in
			$.each( val, function ( idSrc, innerVal ) {
				set( idSrc, innerVal );
			} );
		}
		else if ( id === undefined ) {
			// Set same value for all existing ids
			$.each( multiIds, function ( i, idSrc ) {
				set( idSrc, val );
			} );
		}
		else {
			// Setting an individual property
			set( id, val );
		}

		this.s.multiValue = true;
		this._multiValueCheck();

		return this;
	},

	name: function () {
		return this.s.opts.name;
	},

	node: function () {
		return this.dom.container[0];
	},

	// multiCheck is not publically documented
	set: function ( val, multiCheck ) {
		var decodeFn = function ( d ) {
			return typeof d !== 'string' ?
				d :
				d
					.replace(/&gt;/g, '>')
					.replace(/&lt;/g, '<')
					.replace(/&amp;/g, '&')
					.replace(/&quot;/g, '"')
					.replace(/&#39;/g, '\'')
					.replace(/&#10;/g, '\n');
		};

		this.s.multiValue = false;

		var decode = this.s.opts.entityDecode;
		if ( decode === undefined || decode === true ) {
			if ( $.isArray( val ) ) {
				for ( var i=0, ien=val.length ; i<ien ; i++ ) {
					val[i] = decodeFn( val[i] );
				}
			}
			else {
				val = decodeFn( val );
			}
		}

		this._typeFn( 'set', val );

		if ( multiCheck === undefined || multiCheck === true ) {
			this._multiValueCheck();
		}

		return this;
	},

	show: function ( animate ) {
		var el = this.dom.container;

		if ( animate === undefined ) {
			animate = true;
		}

		if ( this.s.host.display() && animate ) {
			el.slideDown();
		}
		else {
			el.css( 'display', 'block' );
		}
		return this;
	},

	val: function ( val ) {
		return val === undefined ?
			this.get() :
			this.set( val );
	},


	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Internal - Called from Editor only and are not publicly documented -
	 * these APIs can change!
	 */
	compare: function ( value, original ) {
		var compare = this.s.opts.compare || _deepCompare;
		return compare( value, original );
	},

	dataSrc: function () {
		return this.s.opts.data;
	},

	destroy: function () {
		// remove element
		this.dom.container.remove();

		// field's own destroy method if there is one
		this._typeFn( 'destroy' );
		return this;
	},

	multiEditable: function () {
		return this.s.opts.multiEditable;
	},

	multiIds: function () {
		return this.s.multiIds;
	},

	multiInfoShown: function ( show ) {
		this.dom.multiInfo.css( { display: show ? 'block' : 'none' } );
	},

	multiReset: function () {
		this.s.multiIds = [];
		this.s.multiValues = {};
	},

	valFromData: null,

	valToData: null,


	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Private
	 */
	_errorNode: function () {
		return this.dom.fieldError;
	},

	_msg: function ( el, msg, fn ) {
		if ( msg === undefined ) {
			return el.html();
		}

		if ( typeof msg === 'function' ) {
			var editor = this.s.host;
			msg = msg( editor, new DataTable.Api( editor.s.table ) );
		}

		if ( el.parent().is(":visible") ) {
			el.html( msg );

			if ( msg ) {
				el.slideDown( fn ); // fn can be undefined - so jQuery won't execute it
			}
			else {
				el.slideUp( fn );
			}
		}
		else {
			// Not visible, so immediately set, or blank out the element
			el
				.html( msg || '' )
				.css( 'display', msg ? 'block' : 'none' );

			if ( fn ) {
				fn();
			}
		}

		return this;
	},

	_multiValueCheck: function () {
		var last;
		var ids = this.s.multiIds;
		var values = this.s.multiValues;
		var isMultiValue = this.s.multiValue;
		var isMultiEditable = this.s.opts.multiEditable;
		var val;
		var different = false;

		if ( ids ) {
			for ( var i=0 ; i<ids.length ; i++ ) {
				val = values[ ids[i] ];

				if ( i > 0 && ! _deepCompare( val, last ) ) {
					different = true;
					break;
				}

				last = val;
			}
		}

		if ( (different && isMultiValue) || (!isMultiEditable && this.isMultiValue()) ) {
			// Different values or same values, but not multiple editable
			this.dom.inputControl.css( { display: 'none' } );
			this.dom.multi.css( { display: 'block' } );
		}
		else {
			// All the same value
			this.dom.inputControl.css( { display: 'block' } );
			this.dom.multi.css( { display: 'none' } );

			if ( isMultiValue && ! different ) {
				this.set( last, false );
			}
		}

		this.dom.multiReturn.css( {
			display: ids && ids.length > 1 && different && ! isMultiValue ?
				'block' :
				'none'
		} );

		// Update information label
		var i18n =  this.s.host.i18n.multi;
		this.dom.multiInfo.html( isMultiEditable ? i18n.info : i18n.noMulti);
		this.dom.multi.toggleClass( this.s.classes.multiNoEdit, ! isMultiEditable );

		this.s.host._multiInfo();

		return true;
	},

	_typeFn: function ( name /*, ... */ ) {
		// Remove the name from the arguments list, so the rest can be passed
		// straight into the field type
		var args = Array.prototype.slice.call( arguments );
		args.shift();

		// Insert the options as the first parameter - all field type methods
		// take the field's configuration object as the first parameter
		args.unshift( this.s.opts );

		var fn = this.s.type[ name ];
		if ( fn ) {
			return fn.apply( this.s.host, args );
		}
	}
};


Editor.Field.models = {};


/**
 * Initialisation options that can be given to Editor.Field at initialisation
 * time.
 *  @namespace
 */
Editor.Field.defaults = {
	/**
	 * Class name to assign to the field's container element (in addition to the other
	 * classes that Editor assigns by default).
	 *  @type string
	 *  @default <i>Empty string</i>
	 */
	"className": "",

	/**
	 * The data property (`mData` in DataTables terminology) that is used to
	 * read from and write to the table. If not given then it will take the same
	 * value as the `name` that is given in the field object. Note that `data`
	 * can be given as null, which will result in Editor not using a DataTables
	 * row property for the value of the field for either getting or setting
	 * data.
	 *
	 * In previous versions of Editor (1.2-) this was called `dataProp`. The old
	 * name can still be used for backwards compatibility, but the new form is
	 * preferred.
	 *  @type string
	 *  @default <i>Empty string</i>
	 */
	"data": "",

	/**
	 * The default value for the field. Used when creating new rows (editing will
	 * use the currently set value). If given as a function the function will be
	 * executed and the returned value used as the default
	 *
	 * In Editor 1.2 and earlier this field was called `default` - however
	 * `default` is a reserved word in Javascript, so it couldn't be used
	 * unquoted. `default` will still work with Editor 1.3, but the new property
	 * name of `def` is preferred.
	 *  @type string|function
	 *  @default <i>Empty string</i>
	 */
	"def": "",

	/**
	 * Helpful information text about the field that is shown below the input control.
	 *  @type string
	 *  @default <i>Empty string</i>
	 */
	"fieldInfo": "",

	/**
	 * The ID of the field. This is used by the `label` HTML tag as the "for" attribute 
	 * improved accessibility. Although this using this parameter is not mandatory,
	 * it is a good idea to assign the ID to the DOM element that is the input for the
	 * field (if this is applicable).
	 *  @type string
	 *  @default <i>Calculated</i>
	 */
	"id": "",

	/**
	 * The label to display for the field input (i.e. the name that is visually 
	 * assigned to the field).
	 *  @type string
	 *  @default <i>Empty string</i>
	 */
	"label": "",

	/**
	 * Helpful information text about the field that is shown below the field label.
	 *  @type string
	 *  @default <i>Empty string</i>
	 */
	"labelInfo": "",

	/**
	 * The name for the field that is submitted to the server. This is the only
	 * mandatory parameter in the field description object.
	 *  @type string
	 *  @default <i>null</i>
	 */
	"name": null,

	/**
	 * The input control that is presented to the end user. The options available 
	 * are defined by {@link Editor.fieldTypes} and any extensions made 
	 * to that object.
	 *  @type string
	 *  @default text
	 */
	"type": "text",

	/**
	 * Information message for the field - expected to be dynamic
	 *  @type string
	 *  @default <i>Empty string</i>
	 */
	"message": "",

	/**
	 * Allow a field to be editable when multiple rows are selected
	 *  @type boolean
	 *  @default  true
	 */
	"multiEditable": true
};



/**
 * 
 *  @namespace
 */
Editor.Field.models.settings = {
	type: null,
	name: null,
	classes: null,
	opts: null,
	host: null
};



/**
 * 
 *  @namespace
 */
Editor.Field.models.dom = {
	container: null,
	label: null,
	labelInfo: null,
	fieldInfo: null,
	fieldError: null,
	fieldMessage: null
};


/*
 * Models
 */

/**
 * Object models container, for the various models that DataTables has available
 * to it. These models define the objects that are used to hold the active state
 * and configuration of the table.
 *  @namespace
 */
Editor.models = {};


/**
 * Editor makes very few assumptions about how its form will actually be
 * displayed to the end user (where in the DOM, interaction etc), instead
 * focusing on providing form interaction controls only. To actually display
 * a form in the browser we need to use a display controller, and then select
 * which one we want to use at initialisation time using the `display`
 * option. For example a display controller could display the form in a
 * lightbox (as the default display controller does), it could completely
 * empty the document and put only the form in place, ir could work with
 * DataTables to use `fnOpen` / `fnClose` to show the form in a "details" row
 * and so on.
 *
 * Editor has two built-in display controllers ('lightbox' and 'envelope'),
 * but others can readily be created and installed for use as plug-ins. When
 * creating a display controller plug-in you **must** implement the methods
 * in this control. Additionally when closing the display internally you
 * **must** trigger a `requestClose` event which Editor will listen
 * for and act upon (this allows Editor to ask the user if they are sure
 * they want to close the form, for example).
 *  @namespace
 */
Editor.models.displayController = {
	/**
	 * Initialisation method, called by Editor when itself, initialises.
	 *  @param {object} dte The DataTables Editor instance that has requested
	 *    the action - this allows access to the Editor API if required.
	 *  @returns {object} The object that Editor will use to run the 'open'
	 *    and 'close' methods against. If static methods are used then
	 *    just return the object that holds the init, open and close methods,
	 *    however, this allows the display to be created with a 'new'
	 *    instance of an object is the display controller calls for that.
	 *  @type function
	 */
	"init": function ( dte ) {},

	/**
	 * Display the form (add it to the visual display in the document)
	 *  @param {object} dte The DataTables Editor instance that has requested
	 *    the action - this allows access to the Editor API if required.
	 *  @param {element} append The DOM node that contains the form to be
	 *    displayed
	 *  @param {function} [fn] Callback function that is to be executed when
	 *    the form has been displayed. Note that this parameter is optional.
	 */
	"open": function ( dte, append, fn ) {},

	/**
	 * Hide the form (remove it form the visual display in the document)
	 *  @param {object} dte The DataTables Editor instance that has requested
	 *    the action - this allows access to the Editor API if required.
	 *  @param {function} [fn] Callback function that is to be executed when
	 *    the form has been hidden. Note that this parameter is optional.
	 */
	"close": function ( dte, fn ) {}
};



/**
 * Model object for input types which are available to fields (assigned to
 * {@link Editor.fieldTypes}). Any plug-ins which add additional
 * input types to Editor **must** implement the methods in this object 
 * (dummy functions are given in the model so they can be used as defaults
 * if extending this object).
 *
 * All functions in the model are executed in the Editor's instance scope,
 * so you have full access to the settings object and the API methods if
 * required.
 *  @namespace
 *  @example
 *    // Add a simple text input (the 'text' type that is built into Editor
 *    // does this, so you wouldn't implement this exactly as show, but it
 *    // it is a good example.
 *
 *    var Editor = $.fn.Editor;
 *
 *    Editor.fieldTypes.myInput = $.extend( true, {}, Editor.models.type, {
 *      "create": function ( conf ) {
 *        // We store the 'input' element in the configuration object so
 *        // we can easily access it again in future.
 *        conf._input = document.createElement('input');
 *        conf._input.id = conf.id;
 *        return conf._input;
 *      },
 *    
 *      "get": function ( conf ) {
 *        return conf._input.value;
 *      },
 *    
 *      "set": function ( conf, val ) {
 *        conf._input.value = val;
 *      },
 *    
 *      "enable": function ( conf ) {
 *        conf._input.disabled = false;
 *      },
 *    
 *      "disable": function ( conf ) {
 *        conf._input.disabled = true;
 *      }
 *    } );
 */
Editor.models.fieldType = {
	/**
	 * Create the field - this is called when the field is added to the form.
	 * Note that this is called at initialisation time, or when the 
	 * {@link Editor#add} API method is called, not when the form is displayed. 
	 * If you need to know when the form is shown, you can use the API to listen 
	 * for the `open` event.
	 *  @param {object} conf The configuration object for the field in question:
	 *    {@link Editor.models.field}.
	 *  @returns {element|null} The input element (or a wrapping element if a more
	 *    complex input is required) or null if nothing is to be added to the
	 *    DOM for this input type.
	 *  @type function
	 */
	"create": function ( conf ) {},

	/**
	 * Get the value from the field
	 *  @param {object} conf The configuration object for the field in question:
	 *    {@link Editor.models.field}.
	 *  @returns {*} The value from the field - the exact value will depend on the
	 *    formatting required by the input type control.
	 *  @type function
	 */
	"get": function ( conf ) {},

	/**
	 * Set the value for a field
	 *  @param {object} conf The configuration object for the field in question:
	 *    {@link Editor.models.field}.
	 *  @param {*} val The value to set the field to - the exact value will
	 *    depend on the formatting required by the input type control.
	 *  @type function
	 */
	"set": function ( conf, val ) {},

	/**
	 * Enable the field - i.e. allow user interface
	 *  @param {object} conf The configuration object for the field in question:
	 *    {@link Editor.models.field}.
	 *  @type function
	 */
	"enable": function ( conf ) {},

	/**
	 * Disable the field - i.e. disallow user interface
	 *  @param {object} conf The configuration object for the field in question:
	 *    {@link Editor.models.field}.
	 *  @type function
	 */
	"disable": function ( conf ) {}
};



/**
 * Settings object for Editor - this provides the state for each instance of
 * Editor and can be accessed through the instance's `s` property. Note that the
 * settings object is considered to be "private" and thus is liable to change
 * between versions. As such if you do read any of the setting parameters,
 * please keep this in mind when upgrading!
 *  @namespace
 */
Editor.models.settings = {
	/**
	 * URL to submit Ajax data to.
	 * This is directly set by the initialisation parameter / default of the same name.
	 *  @type string
	 *  @default null
	 */
	"ajaxUrl": null,

	/**
	 * Ajax submit function.
	 * This is directly set by the initialisation parameter / default of the same name.
	 *  @type function
	 *  @default null
	 */
	"ajax": null,

	/**
	 * Data source for get and set data actions. This allows Editor to perform
	 * as an Editor for virtually any data source simply by defining additional
	 * data sources.
	 *  @type object
	 *  @default null
	 */
	"dataSource": null,

	/**
	 * DataTable selector, can be anything that the Api supports
	 * This is directly set by the initialisation parameter / default of the same name.
	 *  @type string
	 *  @default null
	 */
	"domTable": null,

	/**
	 * The initialisation object that was given by the user - stored for future reference.
	 * This is directly set by the initialisation parameter / default of the same name.
	 *  @type string
	 *  @default null
	 */
	"opts": null,

	/**
	 * The display controller object for the Form.
	 * This is directly set by the initialisation parameter / default of the same name.
	 *  @type string
	 *  @default null
	 */
	"displayController": null,

	/**
	 * The form fields - see {@link Editor.models.field} for details of the 
	 * objects held in this array.
	 *  @type object
	 *  @default null
	 */
	"fields": {},

	/**
	 * Field order - order that the fields will appear in on the form. Array of strings,
	 * the names of the fields.
	 *  @type array
	 *  @default null
	 */
	"order": [],

	/**
	 * The ID of the row being edited (set to -1 on create and remove actions)
	 *  @type string
	 *  @default null
	 */
	"id": -1,

	/**
	 * Flag to indicate if the form is currently displayed or not and what type of display
	 *  @type string
	 *  @default null
	 */
	"displayed": false,

	/**
	 * Flag to indicate if the form is current in a processing state (true) or not (false)
	 *  @type string
	 *  @default null
	 */
	"processing": false,

	/**
	 * Developer provided identifier for the elements to be edited (i.e. at
	 * `dt-type row-selector` to select rows to edit or delete.
	 *  @type array
	 *  @default null
	 */
	"modifier": null,

	/**
	 * The current form action - 'create', 'edit' or 'remove'. If no current action then
	 * it is set to null.
	 *  @type string
	 *  @default null
	 */
	"action": null,

	/**
	 * JSON property from which to read / write the row's ID property.
	 *  @type string
	 *  @default null
	 */
	"idSrc": null,

	/**
	 * Unique instance counter to be able to remove events
	 */
	"unique": 0
};



/**
 * Model of the buttons that can be used with the {@link Editor#buttons}
 * method for creating and displaying buttons (also the {@link Editor#button}
 * argument option for the {@link Editor#create}, {@link Editor#edit} and 
 * {@link Editor#remove} methods). Although you don't need to extend this object,
 * it is available for reference to show the options available.
 *  @namespace
 */
Editor.models.button = {
	/**
	 * The text to put into the button. This can be any HTML string you wish as 
	 * it will be rendered as HTML (allowing images etc to be shown inside the
	 * button).
	 *  @type string
	 *  @default null
	 */
	"label": null,

	/**
	 * Callback function which the button is activated. For example for a 'submit' 
	 * button you would call the {@link Editor#submit} API method, while for a cancel button
	 * you would call the {@link Editor#close} API method. Note that the function is executed 
	 * in the scope of the Editor instance, so you can call the Editor's API methods 
	 * using the `this` keyword.
	 *  @type function
	 *  @default null
	 */
	"fn": null,

	/**
	 * The CSS class(es) to apply to the button which can be useful for styling buttons 
	 * which preform different functions each with a distinctive visual appearance.
	 *  @type string
	 *  @default null
	 */
	"className": null
};



/**
 * This is really an internal namespace
 *
 *  @namespace
 */
Editor.models.formOptions = {
	/**
	 * Action to take when the return key is pressed when focused in a form
	 * element. Cam be `submit` or `none`. Could also be `blur` or `close`, but
	 * why would you ever want that. Replaces `submitOnReturn` from 1.4.
	 * 
	 * @type string
	 */
	onReturn: 'submit',

	/**
	 * Action to take on blur. Can be `close`, `submit` or `none`. Replaces
	 * `submitOnBlur` from 1.4
	 * 
	 * @type string
	 */
	onBlur: 'close',

	/**
	 * Action to take when the lightbox background is clicked - can be `close`,
	 * `submit`, `blur` or `none`. Replaces `blurOnBackground` from 1.4
	 * 
	 * @type string
	 */
	onBackground: 'blur',

	/**
	 * Close for at the end of the Ajax request. Can be `close` or `none`.
	 * Replaces `closeOnComplete` from 1.4.
	 * 
	 * @type string
	 */
	onComplete: 'close',

	/**
	 * Action to take when the `esc` key is pressed when focused in the form -
	 * can be `close`, `submit`, `blur` or `none`
	 * 
	 * @type string
	 */
	onEsc: 'close',

	/**
	 * Action to take when a field error is detected in the returned JSON - can
	 * be `focus` or `none`
	 * 
	 * @type string
	 */
	onFieldError: 'focus',

	/**
	 * Data to submit to the server when submitting a form. If an option is
	 * selected that results in no data being submitted, the Ajax request will
	 * not be made Can be `all`, `changed` or `allIfChanged`. This effects the
	 * edit action only.
	 *
	 * @type string
	 */
	submit: 'all',

	/**
	 * Field identifier to focus on
	 * 
	 * @type null|integer|string
	 */
	focus: 0,

	/**
	 * Buttons to show in the form
	 * 
	 * @type string|boolean|array|object
	 */
	buttons: true,

	/**
	 * Form title
	 * 
	 * @type string|boolean
	 */
	title: true,

	/**
	 * Form message
	 * 
	 * @type string|boolean
	 */
	message: true,

	/**
	 * DataTables redraw option
	 * 
	 * @type string|boolean
	 */
	drawType: false
};


/*
 * Display controllers
 */

/**
 * Display controllers. See {@link Editor.models.displayController} for
 * full information about the display controller options for Editor. The display
 * controllers given in this object can be utilised by specifying the
 * {@link Editor.defaults.display} option.
 *  @namespace
 */
Editor.display = {};


(function(window, document, $, DataTable) {


var self;

Editor.display.lightbox = $.extend( true, {}, Editor.models.displayController, {
	/*
	 * API methods
	 */
	"init": function ( dte ) {
		self._init();
		return self;
	},

	"open": function ( dte, append, callback ) {
		if ( self._shown ) {
			if ( callback ) {
				callback();
			}
			return;
		}

		self._dte = dte;

		var content = self._dom.content;
		content.children().detach();
		content
			.append( append )
			.append( self._dom.close );

		self._shown = true;
		self._show( callback );
	},

	"close": function ( dte, callback ) {
		if ( !self._shown ) {
			if ( callback ) {
				callback();
			}
			return;
		}

		self._dte = dte;
		self._hide( callback );

		self._shown = false;
	},

	node: function ( dte ) {
		return self._dom.wrapper[0];
	},


	/*
	 * Private methods
	 */
	"_init": function () {
		if ( self._ready ) {
			return;
		}

		var dom = self._dom;
		dom.content = $('div.DTED_Lightbox_Content', self._dom.wrapper);

		dom.wrapper.css( 'opacity', 0 );
		dom.background.css( 'opacity', 0 );
	},


	"_show": function ( callback ) {
		var that = this;
		var dom = self._dom;

		// Mobiles have very poor position fixed abilities, so we need to know
		// when using mobile A media query isn't good enough
		if ( window.orientation !== undefined ) {
			$('body').addClass( 'DTED_Lightbox_Mobile' );
		}

		// Adjust size for the content
		dom.content.css( 'height', 'auto' );
		dom.wrapper.css( {
			top: -self.conf.offsetAni
		} );

		$('body')
			.append( self._dom.background )
			.append( self._dom.wrapper );

		self._heightCalc();

		dom.wrapper
			.stop()
				.animate( {
				opacity: 1,
				top: 0
			}, callback );

		dom.background
			.stop()
			.animate( {
				opacity: 1
			} );

		// Terrible Chrome workaround. Since m53 the footer would be incorrectly
		// offset. This triggers a rerender. See thread 38145
		setTimeout( function () {
			$('div.DTE_Footer').css( 'text-indent', -1 );
		}, 10 );

		// Event handlers - assign on show (and unbind on hide) rather than init
		// since we might need to refer to different editor instances - 12563
		dom.close.bind( 'click.DTED_Lightbox', function (e) {
			self._dte.close();
		} );

		dom.background.bind( 'click.DTED_Lightbox', function (e) {
			self._dte.background();
		} );

		$('div.DTED_Lightbox_Content_Wrapper', dom.wrapper).bind( 'click.DTED_Lightbox', function (e) {
			if ( $(e.target).hasClass('DTED_Lightbox_Content_Wrapper') ) {
				self._dte.background();
			}
		} );

		$(window).bind( 'resize.DTED_Lightbox', function () {
			self._heightCalc();
		} );

		self._scrollTop = $('body').scrollTop();

		// For smaller screens we need to hide the other elements in the
		// document since iOS and Android both mess up display:fixed when
		// the virtual keyboard is shown
		if ( window.orientation !== undefined ) {
			var kids = $('body').children().not( dom.background ).not( dom.wrapper );
			$('body').append( '<div class="DTED_Lightbox_Shown"/>' );
			$('div.DTED_Lightbox_Shown').append( kids );
		}
	},


	"_heightCalc": function () {
		// Set the max-height for the form content
		var dom = self._dom;
		var maxHeight = $(window).height() - (self.conf.windowPadding*2) -
			$('div.DTE_Header', dom.wrapper).outerHeight() -
			$('div.DTE_Footer', dom.wrapper).outerHeight();

		$('div.DTE_Body_Content', dom.wrapper).css(
			'maxHeight',
			maxHeight
		);
	},


	"_hide": function ( callback ) {
		var dom = self._dom;

		if ( !callback ) {
			callback = function () {};
		}

		if ( window.orientation !== undefined  ) {
			var show = $('div.DTED_Lightbox_Shown');
			show.children().appendTo('body');
			show.remove();
		}

		// Restore scroll state
		$('body')
			.removeClass( 'DTED_Lightbox_Mobile' )
			.scrollTop( self._scrollTop );

		dom.wrapper
			.stop()
			.animate( {
				opacity: 0,
				top: self.conf.offsetAni
			}, function () {
				$(this).detach();
				callback();
			} );

		dom.background
			.stop()
			.animate( {
				opacity: 0
			}, function () {
				$(this).detach();
			} );

		// Event handlers
		dom.close.unbind( 'click.DTED_Lightbox' );
		dom.background.unbind( 'click.DTED_Lightbox' );
		$('div.DTED_Lightbox_Content_Wrapper', dom.wrapper).unbind( 'click.DTED_Lightbox' );
		$(window).unbind( 'resize.DTED_Lightbox' );
	},


	/*
	 * Private properties
	 */
	"_dte": null,
	"_ready": false,
	"_shown": false,
	"_dom": {
		"wrapper": $(
			'<div class="DTED DTED_Lightbox_Wrapper">'+
				'<div class="DTED_Lightbox_Container">'+
					'<div class="DTED_Lightbox_Content_Wrapper">'+
						'<div class="DTED_Lightbox_Content">'+
						'</div>'+
					'</div>'+
				'</div>'+
			'</div>'
		),

		"background": $(
			'<div class="DTED_Lightbox_Background"><div/></div>'
		),

		"close": $(
			'<div class="DTED_Lightbox_Close"></div>'
		),

		"content": null
	}
} );

self = Editor.display.lightbox;

self.conf = {
	"offsetAni": 25,
	"windowPadding": 25
};


}(window, document, jQuery, jQuery.fn.dataTable));



(function(window, document, $, DataTable) {


var self;

Editor.display.envelope = $.extend( true, {}, Editor.models.displayController, {
	/*
	 * API methods
	 */
	"init": function ( dte ) {
		self._dte = dte;
		self._init();
		return self;
	},


	"open": function ( dte, append, callback ) {
		self._dte = dte;
		$(self._dom.content).children().detach();
		self._dom.content.appendChild( append );
		self._dom.content.appendChild( self._dom.close );

		self._show( callback );
	},


	"close": function ( dte, callback ) {
		self._dte = dte;
		self._hide( callback );
	},

	node: function ( dte ) {
		return self._dom.wrapper[0];
	},


	/*
	 * Private methods
	 */
	"_init": function () {
		if ( self._ready ) {
			return;
		}

		self._dom.content = $('div.DTED_Envelope_Container', self._dom.wrapper)[0];

		document.body.appendChild( self._dom.background );
		document.body.appendChild( self._dom.wrapper );

		// For IE6-8 we need to make it a block element to read the opacity...
		self._dom.background.style.visbility = 'hidden';
		self._dom.background.style.display = 'block';
		self._cssBackgroundOpacity = $(self._dom.background).css('opacity');
		self._dom.background.style.display = 'none';
		self._dom.background.style.visbility = 'visible';
	},


	"_show": function ( callback ) {
		var that = this;
		var formHeight;

		if ( !callback ) {
			callback = function () {};
		}

		// Adjust size for the content
		self._dom.content.style.height = 'auto';

		var style = self._dom.wrapper.style;
		style.opacity = 0;
		style.display = 'block';

		var targetRow = self._findAttachRow();
		var height = self._heightCalc();
		var width = targetRow.offsetWidth;

		style.display = 'none';
		style.opacity = 1;

		// Prep the display
		self._dom.wrapper.style.width = width+"px";
		self._dom.wrapper.style.marginLeft = -(width/2)+"px";
		self._dom.wrapper.style.top = ($(targetRow).offset().top + targetRow.offsetHeight)+"px";
		self._dom.content.style.top = ((-1 * height) - 20)+"px";

		// Start animating in the background
		self._dom.background.style.opacity = 0;
		self._dom.background.style.display = 'block';
		$(self._dom.background).animate( {
			'opacity': self._cssBackgroundOpacity
		}, 'normal' );

		// Animate in the display
		$(self._dom.wrapper).fadeIn();

		// Slide the slider down to 'open' the view
		if ( self.conf.windowScroll ) {
			// Scroll the window so we can see the editor first
			$('html,body').animate( {
				"scrollTop": $(targetRow).offset().top + targetRow.offsetHeight - self.conf.windowPadding
			}, function () {
				// Now open the editor
				$(self._dom.content).animate( {
					"top": 0
				}, 600, callback );
			} );
		}
		else {
			// Just open the editor without moving the document position
			$(self._dom.content).animate( {
				"top": 0
			}, 600, callback );
		}

		// Event handlers
		$(self._dom.close).bind( 'click.DTED_Envelope', function (e) {
			self._dte.close();
		} );

		$(self._dom.background).bind( 'click.DTED_Envelope', function (e) {
			self._dte.background();
		} );

		$('div.DTED_Lightbox_Content_Wrapper', self._dom.wrapper).bind( 'click.DTED_Envelope', function (e) {
			if ( $(e.target).hasClass('DTED_Envelope_Content_Wrapper') ) {
				self._dte.background();
			}
		} );

		$(window).bind( 'resize.DTED_Envelope', function () {
			self._heightCalc();
		} );
	},


	"_heightCalc": function () {
		var formHeight;

		formHeight = self.conf.heightCalc ?
			self.conf.heightCalc( self._dom.wrapper ) :
			$(self._dom.content).children().height();

		// Set the max-height for the form content
		var maxHeight = $(window).height() - (self.conf.windowPadding*2) -
			$('div.DTE_Header', self._dom.wrapper).outerHeight() -
			$('div.DTE_Footer', self._dom.wrapper).outerHeight();

		$('div.DTE_Body_Content', self._dom.wrapper).css('maxHeight', maxHeight);

		return $(self._dte.dom.wrapper).outerHeight();
	},


	"_hide": function ( callback ) {
		if ( !callback ) {
			callback = function () {};
		}

		$(self._dom.content).animate( {
			"top": -(self._dom.content.offsetHeight+50)
		}, 600, function () {
			$([self._dom.wrapper, self._dom.background]).fadeOut( 'normal', callback );
		} );

		// Event handlers
		$(self._dom.close).unbind( 'click.DTED_Lightbox' );
		$(self._dom.background).unbind( 'click.DTED_Lightbox' );
		$('div.DTED_Lightbox_Content_Wrapper', self._dom.wrapper).unbind( 'click.DTED_Lightbox' );
		$(window).unbind( 'resize.DTED_Lightbox' );
	},


	"_findAttachRow": function () {
		var dt = $(self._dte.s.table).DataTable();

		// Figure out where we want to put the form display
		if ( self.conf.attach === 'head' ) {
			return dt.table().header();
		}
		else if ( self._dte.s.action === 'create' ) {
			return dt.table().header();
		}
		else {
			return dt.row( self._dte.s.modifier ).node();
		}
	},


	/*
	 * Private properties
	 */
	"_dte": null,
	"_ready": false,
	"_cssBackgroundOpacity": 1, // read from the CSS dynamically, but stored for future reference


	"_dom": {
		"wrapper": $(
			'<div class="DTED DTED_Envelope_Wrapper">'+
				'<div class="DTED_Envelope_Shadow"></div>'+
				'<div class="DTED_Envelope_Container"></div>'+
			'</div>'
		)[0],

		"background": $(
			'<div class="DTED_Envelope_Background"><div/></div>'
		)[0],

		"close": $(
			'<div class="DTED_Envelope_Close">&times;</div>'
		)[0],

		"content": null
	}
} );


// Assign to 'self' for easy referencing of our own object!
self = Editor.display.envelope;


// Configuration object - can be accessed globally using 
// $.fn.Editor.display.envelope.conf (!)
self.conf = {
	"windowPadding": 50,
	"heightCalc": null,
	"attach": "row",
	"windowScroll": true
};


}(window, document, jQuery, jQuery.fn.dataTable));


/*
 * Prototype includes
 */


/**
 * Add a new field to the from. This is the method that is called automatically when
 * fields are given in the initialisation objects as {@link Editor.defaults.fields}.
 *  @memberOf Editor
 *  @param {object|array} field The object that describes the field (the full
 *    object is described by {@link Editor.model.field}. Note that multiple
 *    fields can be given by passing in an array of field definitions.
 *  @param {string} [after] Existing field to insert the new field after. This
 *    can be `undefined` (insert at end), `null` (insert at start) or `string`
 *    the field name to insert after.
 */
Editor.prototype.add = function ( cfg, after )
{
	// Allow multiple fields to be added at the same time
	if ( $.isArray( cfg ) ) {
		for ( var i=0, iLen=cfg.length ; i<iLen ; i++ ) {
			this.add( cfg[i] );
		}
	}
	else {
		var name = cfg.name;

		if ( name === undefined ) {
			throw "Error adding field. The field requires a `name` option";
		}

		if ( this.s.fields[ name ] ) {
			throw "Error adding field '"+name+"'. A field already exists with this name";
		}

		// Allow the data source to add / modify the field properties
		// Dev: would this be better as an event `preAddField`? And have the
		// data sources init only once, but can listen for such events? More
		// complexity, but probably more flexible...
		this._dataSource( 'initField', cfg );

		this.s.fields[ name ] = new Editor.Field( cfg, this.classes.field, this );

		if ( after === undefined ) {
			this.s.order.push( name );
		}
		else if ( after === null ) {
			this.s.order.unshift( name );
		}
		else {
			var idx = $.inArray( after, this.s.order );
			this.s.order.splice( idx+1, 0, name );
		}
	}

	this._displayReorder( this.order() );

	return this;
};


/**
 * Perform background activation tasks.
 * 
 * This is NOT publicly documented on the Editor web-site, but rather can be
 * used by display controller plug-ins to perform the required task on
 * background activation.
 *
 * @return {Editor} Editor instance, for chaining
 */
Editor.prototype.background = function ()
{
	var onBackground = this.s.editOpts.onBackground;

	if ( typeof onBackground === 'function' ) {
		onBackground( this );
	}
	else if ( onBackground === 'blur' ) {
		this.blur();
	}
	else if ( onBackground === 'close' ) {
		this.close();
	}
	else if ( onBackground === 'submit' ) {
		this.submit();
	}

	return this;
};


/**
 * Blur the currently displayed editor.
 *
 * A blur is different from a `close()` in that it might cause either a close or
 * the form to be submitted. A typical example of a blur would be clicking on
 * the background of the bubble or main editing forms - i.e. it might be a
 * close, or it might submit depending upon the configuration, while a click on
 * the close box is a very definite close.
 *
 * @return {Editor} Editor instance, for chaining
 */
Editor.prototype.blur = function ()
{
	this._blur();

	return this;
};



Editor.prototype.bubble = function ( cells, fieldNames, show, opts )
{
	var that = this;

	// Some other field in inline edit mode?
	if ( this._tidy( function () { that.bubble( cells, fieldNames, opts ); } ) ) {
		return this;
	}

	// Argument shifting
	if ( $.isPlainObject( fieldNames ) ) {
		opts = fieldNames;
		fieldNames = undefined;
		show = true;
	}
	else if ( typeof fieldNames === 'boolean' ) {
		show = fieldNames;
		fieldNames = undefined;
		opts = undefined;
	}

	if ( $.isPlainObject( show ) ) {
		opts = show;
		show = true;
	}

	if ( show === undefined ) {
		show = true;
	}

	opts = $.extend( {}, this.s.formOptions.bubble, opts );

	var editFields = this._dataSource( 'individual', cells, fieldNames );

	this._edit( cells, editFields, 'bubble' );

	var namespace = this._formOptions( opts );
	var ret = this._preopen( 'bubble' );
	if ( ! ret ) {
		return this;
	}

	// Keep the bubble in position on resize
	$(window).on( 'resize.'+namespace, function () {
		that.bubblePosition();
	} );

	// Store the nodes that are being used so the bubble can be positioned
	var nodes = [];
	this.s.bubbleNodes = nodes.concat.apply( nodes, _pluck( editFields, 'attach' ) );

	// Create container display
	var classes = this.classes.bubble;
	var background = $( '<div class="'+classes.bg+'"><div/></div>' );
	var container = $(
			'<div class="'+classes.wrapper+'">'+
				'<div class="'+classes.liner+'">'+
					'<div class="'+classes.table+'">'+
						'<div class="'+classes.close+'" />'+
						'<div class="DTE_Processing_Indicator"><span></div>'+
					'</div>'+
				'</div>'+
				'<div class="'+classes.pointer+'" />'+
			'</div>'
		);

	if ( show ) {
		container.appendTo( 'body' );
		background.appendTo( 'body' );
	}

	var liner = container.children().eq(0);
	var table = liner.children();
	var close = table.children();
	liner.append( this.dom.formError );
	table.prepend( this.dom.form );

	if ( opts.message ) {
		liner.prepend( this.dom.formInfo );
	}

	if ( opts.title ) {
		liner.prepend( this.dom.header );
	}

	if ( opts.buttons ) {
		table.append( this.dom.buttons );
	}

	var pair = $().add( container ).add( background );
	this._closeReg( function ( submitComplete ) {
		pair.animate(
			{ opacity: 0 },
			function () {
				pair.detach();

				$(window).off( 'resize.'+namespace );

				// Clear error messages "offline"
				that._clearDynamicInfo();
			}
		);
	} );

	// Close event handlers
	background.click( function () {
		that.blur();
	} );

	close.click( function () {
		that._close();
	} );

	this.bubblePosition();

	pair.animate( { opacity: 1 } );

	this._focus( this.s.includeFields, opts.focus );
	this._postopen( 'bubble' );

	return this;
};


/**
 * Reposition the editing bubble (`bubble()`) when it is visible. This can be
 * used to update the bubble position if other elements on the page change
 * position. Editor will automatically call this method on window resize.
 *
 * @return {Editor} Editor instance, for chaining
 */
Editor.prototype.bubblePosition = function ()
{
	var
		wrapper = $('div.DTE_Bubble'),
		liner = $('div.DTE_Bubble_Liner'),
		nodes = this.s.bubbleNodes;

	// Average the node positions to insert the container
	var position = { top: 0, left: 0, right: 0, bottom: 0 };

	$.each( nodes, function (i, node) {
		var pos = $(node).offset();
		node = $(node).get(0);

		position.top += pos.top;
		position.left += pos.left;
		position.right += pos.left + node.offsetWidth;
		position.bottom += pos.top + node.offsetHeight;
	} );

	position.top /= nodes.length;
	position.left /= nodes.length;
	position.right /= nodes.length;
	position.bottom /= nodes.length;

	var
		top = position.top,
		left = (position.left + position.right) / 2,
		width = liner.outerWidth(),
		visLeft = left - (width / 2),
		visRight = visLeft + width,
		docWidth = $(window).width(),
		padding = 15,
		classes = this.classes.bubble;

	wrapper.css( {
		top: top,
		left: left
	} );

	// Correct for overflow from the top of the document by positioning below
	// the field if needed
	if ( liner.length && liner.offset().top < 0 ) {
		wrapper
			.css( 'top', position.bottom )
			.addClass( 'below' );
	}
	else {
		wrapper.removeClass( 'below' );
	}

	// Attempt to correct for overflow to the right of the document
	if ( visRight+padding > docWidth ) {
		var diff = visRight - docWidth;

		// If left overflowing, that takes priority
		liner.css( 'left', visLeft < padding ?
			-(visLeft-padding) :
			-(diff+padding)
		);
	}
	else {
		// Correct overflow to the left
		liner.css( 'left', visLeft < padding ? -(visLeft-padding) : 0 );
	}

	return this;
};


/**
 * Setup the buttons that will be shown in the footer of the form - calling this
 * method will replace any buttons which are currently shown in the form.
 *  @param {array|object} buttons A single button definition to add to the form or
 *    an array of objects with the button definitions to add more than one button.
 *    The options for the button definitions are fully defined by the
 *    {@link Editor.models.button} object.
 *  @param {string} buttons.text The text to put into the button. This can be any
 *    HTML string you wish as it will be rendered as HTML (allowing images etc to 
 *    be shown inside the button).
 *  @param {function} [buttons.action] Callback function which the button is activated.
 *    For example for a 'submit' button you would call the {@link Editor#submit} method,
 *    while for a cancel button you would call the {@link Editor#close} method. Note that
 *    the function is executed in the scope of the Editor instance, so you can call
 *    the Editor's API methods using the `this` keyword.
 *  @param {string} [buttons.className] The CSS class(es) to apply to the button
 *    which can be useful for styling buttons which preform different functions
 *    each with a distinctive visual appearance.
 *  @return {Editor} Editor instance, for chaining
 */
Editor.prototype.buttons = function ( buttons )
{
	var that = this;

	if ( buttons === '_basic' ) {
		// Special string to create a basic button - undocumented
		buttons = [ {
			text: this.i18n[ this.s.action ].submit,
			action: function () { this.submit(); }
		} ];
	}
	else if ( ! $.isArray( buttons ) ) {
		// Allow a single button to be passed in as an object with an array
		buttons = [ buttons ];
	}

	$(this.dom.buttons).empty();

	$.each( buttons, function ( i, btn ) {
		if ( typeof btn === 'string' ) {
			btn = {
				text: btn,
				action: function () { this.submit(); }
			};
		}

		var text = btn.text || btn.label;
		var action = btn.action || btn.fn;

		$( '<button/>', {
				'class': that.classes.form.button+(btn.className ? ' '+btn.className : '')
			} )
			.html( typeof text === 'function' ?
				text( that ) :
				text || ''
			)
			.attr( 'tabindex', btn.tabIndex !== undefined ? btn.tabIndex : 0 )
			.on( 'keyup', function (e) {
				if ( e.keyCode === 13 && action ) {
					action.call( that );
				}
			} )
			.on( 'keypress', function (e) {
				// Stop the browser activating the click event - if we don't
				// have this and the Ajax return is fast, the keyup in
				// `_formOptions()` might trigger another submit
				if ( e.keyCode === 13 ) {
					e.preventDefault();
				}
			} )
			.on( 'click', function (e) {
				e.preventDefault();

				if ( action ) {
					action.call( that );
				}
			} )
			.appendTo( that.dom.buttons );
	} );

	return this;
};


/**
 * Remove fields from the form (fields are those that have been added using the
 * {@link Editor#add} method or the `fields` initialisation option). A single,
 * multiple or all fields can be removed at a time based on the passed parameter.
 * Fields are identified by the `name` property that was given to each field
 * when added to the form.
 *  @param {string|array} [fieldName] Field or fields to remove from the form. If
 *    not given then all fields are removed from the form. If given as a string
 *    then the single matching field will be removed. If given as an array of
 *    strings, then all matching fields will be removed.
 *  @return {Editor} Editor instance, for chaining
 *
 *  @example
 *    // Clear the form of current fields and then add a new field 
 *    // before displaying a 'create' display
 *    editor.clear();
 *    editor.add( {
 *      "label": "User name",
 *      "name": "username"
 *    } );
 *    editor.create( "Create user" );
 *
 *  @example
 *    // Remove an individual field
 *    editor.clear( "username" );
 *
 *  @example
 *    // Remove multiple fields
 *    editor.clear( [ "first_name", "last_name" ] );
 */
Editor.prototype.clear = function ( fieldName )
{
	var that = this;
	var fields = this.s.fields;

	if ( typeof fieldName === 'string' ) {
		// Remove an individual form element
		that.field(fieldName).destroy();
		delete fields[ fieldName ];

		var orderIdx = $.inArray( fieldName, this.s.order );
		this.s.order.splice( orderIdx, 1 );

		var includeIdx = $.inArray( fieldName, this.s.includeFields );
		if ( includeIdx !== -1 ) {
			this.s.includeFields.splice( includeIdx, 1 );
		}
	}
	else {
		$.each( this._fieldNames( fieldName ), function (i, name) {
			that.clear( name );
		} );
	}

	return this;
};


/**
 * Close the form display.
 * 
 * Note that `close()` will close any of the three Editor form types (main,
 * bubble and inline).
 *
 *  @return {Editor} Editor instance, for chaining
 */
Editor.prototype.close = function ()
{
	this._close( false );

	return this;
};


/**
 * Create a new record - show the form that allows the user to enter information
 * for a new row and then subsequently submit that data.
 *  @param {boolean} [show=true] Show the form or not.
 * 
 *  @example
 *    // Show the create form with a submit button
 *    editor
 *      .title( 'Add new record' )
 *      .buttons( {
 *        "label": "Save",
 *        "fn": function () {
 *          this.submit();
 *        }
 *      } )
 *      .create();
 * 
 *  @example
 *    // Don't show the form and automatically submit it after programatically 
 *    // setting the values of fields (and using the field defaults)
 *    editor
 *      create()
 *      set( 'name',   'Test user' )
 *      set( 'access', 'Read only' )
 *      submit();
 */
Editor.prototype.create = function ( arg1, arg2, arg3, arg4 )
{
	var that = this;
	var fields = this.s.fields;
	var count = 1;

	// Some other field in inline edit mode?
	if ( this._tidy( function () { that.create( arg1, arg2, arg3, arg4 ); } ) ) {
		return this;
	}

	// Multi-row creation support (only supported by the 1.3+ style of calling
	// this method, so a max of three arguments
	if ( typeof arg1 === 'number' ) {
		count = arg1;
		arg1 = arg2;
		arg2 = arg3;
	}

	// Set up the edit fields for submission
	this.s.editFields = {};
	for ( var i=0 ; i<count ; i++ ) {
		this.s.editFields[ i ] = {
			fields: this.s.fields
		};
	}

	var argOpts = this._crudArgs( arg1, arg2, arg3, arg4 );

	this.s.mode = 'main';
	this.s.action = "create";
	this.s.modifier = null;
	this.dom.form.style.display = 'block';

	this._actionClass();

	// Allow all fields to be displayed for the create form
	this._displayReorder( this.fields() );

	// Set the default for the fields
	$.each( fields, function ( name, field ) {
		field.multiReset();

		// Set a value marker for each multi, so the field
		// knows what the id's are (ints in this case)
		for ( var i=0 ; i<count ; i++ ) {
			field.multiSet( i, field.def() );
		}

		field.set( field.def() );
	} );

	this._event( 'initCreate' );
	this._assembleMain();
	this._formOptions( argOpts.opts );

	argOpts.maybeOpen();

	return this;
};

/**
 * Create a dependent link between two or more fields. This method is used to
 * listen for a change in a field's value which will trigger updating of the
 * form. This update can consist of updating an options list, changing values
 * or making fields hidden / visible.
 *
 * @param {string} parent The name of the field to listen to changes from
 * @param {string|object|function} url Callback definition. This can be:
 *   * A string, which will be used as a URL to submit the request for update to
 *   * An object, which is used to extend an Ajax object for the request. The
 *     `url` parameter must be specified.
 *   * A function, which is used as a callback, allowing non-ajax updates.
 * @return {Editor} Editor instance, for chaining
 */
Editor.prototype.dependent = function ( parent, url, opts ) {
	if ( $.isArray( parent ) ) {
		for ( var i=0, ien=parent.length ; i<ien ; i++ ) {
			this.dependent( parent[i], url, opts );
		}

		return this;
	}

	var that = this;
	var field = this.field( parent );
	var ajaxOpts = {
		type: 'POST',
		dataType: 'json'
	};

	opts = $.extend( {
		event: 'change',
		data: null,
		preUpdate: null,
		postUpdate: null
	}, opts );

	var update = function ( json ) {
		if ( opts.preUpdate ) {
			opts.preUpdate( json );
		}

		// Field specific
		$.each( {
			labels:   'label',
			options:  'update',
			values:   'val',
			messages: 'message',
			errors:   'error'
		}, function ( jsonProp, fieldFn ) {
			if ( json[ jsonProp ] ) {
				$.each( json[ jsonProp ], function ( field, val ) {
					that.field( field )[ fieldFn ]( val );
				} );
			}
		} );

		// Form level
		$.each( [ 'hide', 'show', 'enable', 'disable' ], function ( i, key ) {
			if ( json[ key ] ) {
				that[ key ]( json[ key ] );
			}
		} );

		if ( opts.postUpdate ) {
			opts.postUpdate( json );
		}
	};

	// Use a delegate handler to account for field elements which are added and
	// removed after `depenedent` has been called
	$(field.node()).on( opts.event, function (e) {
		// Make sure that it was one of the field's elements that triggered the ev
		if ( $( field.node() ).find( e.target ).length === 0 ) {
			return;
		}

		var data = {};
		data.rows = that.s.editFields ?
			_pluck( that.s.editFields, 'data' ) :
			null;
		data.row = data.rows ?
			data.rows[0] :
			null;
		data.values = that.val();

		if ( opts.data ) {
			var ret = opts.data( data );

			if ( ret ) {
				opts.data = ret;
			}
		}

		if ( typeof url === 'function' ) {
			var o = url( field.val(), data, update );

			if ( o ) {
				update( o );
			}
		}
		else {
			if ( $.isPlainObject( url ) ) {
				$.extend( ajaxOpts, url );
			}
			else {
				ajaxOpts.url = url;
			}

			$.ajax( $.extend( ajaxOpts, {
				url: url,
				data: data,
				success: update
			} ) );
		}
	} );

	return this;
};


/**
 * Destroy the Editor instance, cleaning up fields, display and event handlers
 */
Editor.prototype.destroy = function ()
{
	if ( this.s.displayed ) {
		this.close();
	}

	this.clear();

	var controller = this.s.displayController;
	if ( controller.destroy ) {
		controller.destroy( this );
	}

	$(document).off( '.dte'+this.s.unique );

	this.dom = null;
	this.s = null;
};


/**
 * Disable one or more field inputs, disallowing subsequent user interaction with the 
 * fields until they are re-enabled.
 *  @param {string|array} name The field name (from the `name` parameter given when
 *   originally setting up the field) to disable, or an array of field names to disable
 *   multiple fields with a single call.
 *  @return {Editor} Editor instance, for chaining
 * 
 *  @example
 *    // Show a 'create' record form, but with a field disabled
 *    editor.disable( 'account_type' );
 *    editor.create( 'Add new user', {
 *      "label": "Save",
 *      "fn": function () { this.submit(); }
 *    } );
 * 
 *  @example
 *    // Disable multiple fields by using an array of field names
 *    editor.disable( ['account_type', 'access_level'] );
 */
Editor.prototype.disable = function ( name )
{
	var that = this;

	$.each( this._fieldNames( name ), function ( i, n ) {
		that.field(n).disable();
	} );

	return this;
};


/**
 * Display, or remove the editing form from the display
 *  @param {boolean} show Show (`true`) or hide (`false`)
 *  @return {Editor} Editor instance, for chaining
 */
Editor.prototype.display = function ( show )
{
	if ( show === undefined ) {
		return this.s.displayed;
	}
	return this[ show ? 'open' : 'close' ]();
};


/**
 * Fields which are currently displayed
 *  @return {string[]} Field names that are shown
 */
Editor.prototype.displayed = function ()
{
	return $.map( this.s.fields, function ( field, name ) {
		return field.displayed() ? name : null;
	} );
};


/**
 * Get display controller node
 *
 *  @return {node} Display controller host element
 */
Editor.prototype.displayNode = function ()
{
	return this.s.displayController.node( this );
};


/**
 * Edit a record - show the form, pre-populated with the data that is in the given 
 * DataTables row, that allows the user to enter information for the row to be modified
 * and then subsequently submit that data.
 *  @param {node} items The TR element from the DataTable that is to be edited
 *  @param {boolean} [show=true] Show the form or not.
 *  @return {Editor} Editor instance, for chaining
 * 
 *  @example
 *    // Show the edit form for the first row in the DataTable with a submit button
 *    editor.edit( $('#example tbody tr:eq(0)')[0], 'Edit record', {
 *      "label": "Update",
 *      "fn": function () { this.submit(); }
 *    } );
 *
 *  @example
 *    // Use the title and buttons API methods to show an edit form (this provides
 *    // the same result as example above, but is a different way of achieving it
 *    editor.title( 'Edit record' );
 *    editor.buttons( {
 *      "label": "Update",
 *      "fn": function () { this.submit(); }
 *    } );
 *    editor.edit( $('#example tbody tr:eq(0)')[0] );
 * 
 *  @example
 *    // Automatically submit an edit without showing the user the form
 *    editor.edit( TRnode, null, null, false );
 *    editor.set( 'name', 'Updated name' );
 *    editor.set( 'access', 'Read only' );
 *    editor.submit();
 */
Editor.prototype.edit = function ( items, arg1, arg2, arg3, arg4 )
{
	var that = this;

	// Some other field in inline edit mode?
	if ( this._tidy( function () { that.edit( items, arg1, arg2, arg3, arg4 ); } ) ) {
		return this;
	}

	var argOpts = this._crudArgs( arg1, arg2, arg3, arg4 );

	this._edit( items, this._dataSource( 'fields', items ), 'main' );
	this._assembleMain();
	this._formOptions( argOpts.opts );

	argOpts.maybeOpen();

	return this;
};


/**
 * Enable one or more field inputs, restoring user interaction with the fields.
 *  @param {string|array} name The field name (from the `name` parameter given when
 *   originally setting up the field) to enable, or an array of field names to enable
 *   multiple fields with a single call.
 *  @return {Editor} Editor instance, for chaining
 * 
 *  @example
 *    // Show a 'create' form with buttons which will enable and disable certain fields
 *    editor.create( 'Add new user', [
 *      {
 *        "label": "User name only",
 *        "fn": function () {
 *          this.enable('username');
 *          this.disable( ['first_name', 'last_name'] );
 *        }
 *      }, {
 *        "label": "Name based",
 *        "fn": function () {
 *          this.disable('username');
 *          this.enable( ['first_name', 'last_name'] );
 *        }
 *      }, {
 *        "label": "Submit",
 *        "fn": function () { this.submit(); }
 *      }
 *    );
 */
Editor.prototype.enable = function ( name )
{
	var that = this;

	$.each( this._fieldNames( name ), function ( i, n ) {
		that.field(n).enable();
	} );

	return this;
};


/**
 * Show that a field, or the form globally, is in an error state. Note that
 * errors are cleared on each submission of the form.
 *  @param {string} [name] The name of the field that is in error. If not
 *    given then the global form error display is used.
 *  @param {string} msg The error message to show
 *  @return {Editor} Editor instance, for chaining
 * 
 *  @example
 *    // Show an error if the field is required
 *    editor.create( 'Add new user', {
 *      "label": "Submit",
 *      "fn": function () {
 *        if ( this.get('username') === '' ) {
 *          this.error( 'username', 'A user name is required' );
 *          return;
 *        }
 *        this.submit();
 *      }
 *    } );
 * 
 *  @example
 *    // Show a field and a global error for a required field
 *    editor.create( 'Add new user', {
 *      "label": "Submit",
 *      "fn": function () {
 *        if ( this.get('username') === '' ) {
 *          this.error( 'username', 'A user name is required' );
 *          this.error( 'The data could not be saved because it is incomplete' );
 *          return;
 *        }
 *        this.submit();
 *      }
 *    } );
 */
Editor.prototype.error = function ( name, msg )
{
	if ( msg === undefined ) {
		// Global error
		this._message( this.dom.formError, name );
	}
	else {
		// Field error
		this.field( name ).error( msg );
	}

	return this;
};


/**
 * Get a field object, configured for a named field, which can then be
 * manipulated through its API. This function effectively acts as a
 * proxy to the field extensions, allowing easy access to the methods
 * for a named field. The methods that are available depend upon the field
 * type plug-in for Editor.
 *
 *   @param {string} name Field name to be obtained
 *   @return {Editor.Field} Field instance
 *
 *   @example
 *     // Update the values available in a select list
 *     editor.field('island').update( [
 *       'Lewis and Harris',
 *       'South Uist',
 *       'North Uist',
 *       'Benbecula',
 *       'Barra'
 *     ] );
 *
 *   @example
 *     // Equivalent calls
 *     editor.field('name').set('John Smith');
 *
 *     // results in the same action as:
 *     editor.set('John Smith');
 */
Editor.prototype.field = function ( name )
{
	var fields = this.s.fields;

	if ( ! fields[name] ) {
		throw 'Unknown field name - '+name;
	}

	return fields[ name ];
};


/**
 * Get a list of the fields that are used by the Editor instance.
 *  @returns {string[]} Array of field names
 * 
 *  @example
 *    // Get current fields and move first item to the end
 *    var fields = editor.fields();
 *    var first = fields.shift();
 *    fields.push( first );
 *    editor.order( fields );
 */
Editor.prototype.fields = function ()
{
	return $.map( this.s.fields, function ( field, name ) {
		return name;
	} );
};

/**
 * Get data object for a file from a table and id
 *
 * @param  {string} name Table name
 * @param  {string|number} id Primary key identifier
 * @return {object} Table information
 */
Editor.prototype.file = _api_file;

/**
 * Get data objects for available files
 *
 * @param  {string} [name] Table name
 * @return {object} Table array
 */
Editor.prototype.files = _api_files;


/**
 * Get the value of a field
 *  @param {string|array} [name] The field name (from the `name` parameter given
 *    when originally setting up the field) to disable. If not given, then an
 *    object of fields is returned, with the value of each field from the
 *    instance represented in the array (the object properties are the field
 *    names). Also an array of field names can be given to get a collection of
 *    data from the form.
 *  @returns {*|object} Value from the named field
 * 
 *  @example
 *    // Client-side validation - check that a field has been given a value 
 *    // before submitting the form
 *    editor.create( 'Add new user', {
 *      "label": "Submit",
 *      "fn": function () {
 *        if ( this.get('username') === '' ) {
 *          this.error( 'username', 'A user name is required' );
 *          return;
 *        }
 *        this.submit();
 *      }
 *    } );
 */
Editor.prototype.get = function ( name )
{
	var that = this;

	if ( ! name ) {
		name = this.fields();
	}

	if ( $.isArray( name ) ) {
		var out = {};

		$.each( name, function (i, n) {
			out[n] = that.field(n).get();
		} );

		return out;
	}

	return this.field(name).get();
};


/**
 * Remove a field from the form display. Note that the field will still be submitted
 * with the other fields in the form, but it simply won't be visible to the user.
 *  @param {string|array} [name] The field name (from the `name` parameter given when
 *   originally setting up the field) to hide or an array of names. If not given then all 
 *   fields are hidden.
 *  @param {boolean} [animate=true] Animate if visible
 *  @return {Editor} Editor instance, for chaining
 * 
 *  @example
 *    // Show a 'create' record form, but with some fields hidden
 *    editor.hide( 'account_type' );
 *    editor.hide( 'access_level' );
 *    editor.create( 'Add new user', {
 *      "label": "Save",
 *      "fn": function () { this.submit(); }
 *    } );
 *
 *  @example
 *    // Show a single field by hiding all and then showing one
 *    editor.hide();
 *    editor.show('access_type');
 */
Editor.prototype.hide = function ( names, animate )
{
	var that = this;

	$.each( this._fieldNames( names ), function (i, n) {
		that.field( n ).hide( animate );
	} );

	return this;
};


/**
 * Determine if there is an error state in the form, either the form's global
 * error message, or one or more fields.
 *
 * @param {string|array|undefined} [inNames] The field names to check. All
 *   fields checked if undefined.
 * @return {boolean} `true` if there is an error in the form
 */
Editor.prototype.inError = function ( inNames )
{
	// Is there a global error?
	if ( $(this.dom.formError).is(':visible') ) {
		return true;
	}

	// Field specific
	var names = this._fieldNames( inNames );

	for ( var i=0, ien=names.length ; i<ien ; i++ ) {
		if ( this.field( names[i] ).inError() ) {
			return true;
		}
	}

	return false;
};


/**
 * Inline editing for a single field. This method provides a method to allow
 * end users to very quickly edit fields in place. For example, a user could
 * simply click on a cell in a table, the contents of which would be replaced
 * with the editing input field for that cell.
 *
 * @param {string|node|DataTables.Api|cell-selector} cell The cell or field to
 *   be edited (note that for table editing this must be a cell - for standalone
 *   editing it can also be the field name to edit).
 * @param {string} [fieldName] The field name to be edited. This parameter is
 *   optional. If not provided, Editor will attempt to resolve the correct field
 *   from the cell / element given as the first parameter. If it is unable to do
 *   so, it will throw an error.
 * @param {object} [opts] Inline editing options - see the `form-options` type
 *  @return {Editor} Editor instance, for chaining
 */
Editor.prototype.inline = function ( cell, fieldName, opts )
{
	var that = this;

	// Argument shifting
	if ( $.isPlainObject( fieldName ) ) {
		opts = fieldName;
		fieldName = undefined;
	}

	opts = $.extend( {}, this.s.formOptions.inline, opts );

	var editFields = this._dataSource( 'individual', cell, fieldName );
	var node, field;
	var countOuter=0, countInner;
	var closed=false;
	var classes = this.classes.inline;

	// Read the individual cell information from the editFields object
	$.each( editFields, function ( i, editField ) {
		// Only a single row
		if ( countOuter > 0 ) {
			throw 'Cannot edit more than one row inline at a time';
		}

		node = $(editField.attach[0]);

		// Only a single item in that row
		countInner = 0;
		$.each( editField.displayFields, function ( j, f ) {
			if ( countInner > 0 ) {
				throw 'Cannot edit more than one field inline at a time';
			}

			field = f;
			countInner++;
		} );

		countOuter++;

		// If only changed values are to be submitted, then only allow the
		// individual field that we are editing to be edited.
		// This is currently disabled, as I'm not convinced that it is actually
		// useful!
		// if ( opts.submit === 'changed' ) {
		// 	editField.fields = editField.displayFields;
		// }
	} );
	
	// Already in edit mode for this cell?
	if ( $('div.DTE_Field', node).length ) {
		return this;
	}

	// Some other field in inline edit mode?
	if ( this._tidy( function () { that.inline( cell, fieldName, opts ); } ) ) {
		return this;
	}

	// Start a full row edit, but don't display - we will be showing the field
	this._edit( cell, editFields, 'inline' );
	var namespace = this._formOptions( opts );

	var ret = this._preopen( 'inline' );
	if ( ! ret ) {
		return this;
	}

	// Remove from DOM, keeping event handlers, and include text nodes in remove
	var children = node.contents().detach();

	node.append( $(
		'<div class="'+classes.wrapper+'">'+
			'<div class="'+classes.liner+'">'+
				'<div class="DTE_Processing_Indicator"><span/></div>'+
			'</div>'+
			'<div class="'+classes.buttons+'"/>'+
		'</div>'
	) );

	node.find('div.'+classes.liner.replace(/ /g, '.'))
		.append( field.node() )
		.append( this.dom.formError );

	if ( opts.buttons ) {
		// Use prepend for the CSS, so we can float the buttons right
		node.find('div.'+classes.buttons.replace(/ /g, '.')).append( this.dom.buttons );
	}

	this._closeReg( function ( submitComplete ) {
		// Mark that this specific inline edit has closed
		closed = true;

		$(document).off( 'click'+namespace );

		// If there was no submit, we need to put the DOM back as it was. If
		// there was a submit, the write of the new value will set the DOM to
		// how it should be
		if ( ! submitComplete ) {
			node.contents().detach();
			node.append( children );
		}

		// Clear error messages "offline"
		that._clearDynamicInfo();
	} );

	// Submit and blur actions
	setTimeout( function () {
		// If already closed, possibly due to some other aspect of the event
		// that triggered the inline call, don't add the event listener - it
		// isn't needed (and is dangerous)
		if ( closed ) {
			return;
		}

		$(document).on( 'click'+namespace, function ( e ) {
			// Was the click inside or owned by the editing node? If not, then
			// come out of editing mode.

			// andSelf is deprecated in jQ1.8, but we want 1.7 compat
			var back = $.fn.addBack ? 'addBack' : 'andSelf';

			if ( ! field._typeFn( 'owns', e.target ) && 
				 $.inArray( node[0], $(e.target).parents()[ back ]() ) === -1 )
			{
				that.blur();
			}
		} );
	}, 0 );

	this._focus( [ field ], opts.focus );
	this._postopen( 'inline' );

	return this;
};


/**
 * Show an information message for the form as a whole, or for an individual
 * field. This can be used to provide helpful information to a user about an
 * individual field, or more typically the form (for example when deleting
 * a record and asking for confirmation).
 *  @param {string} [name] The name of the field to show the message for. If not
 *    given then a global message is shown for the form
 *  @param {string|function} msg The message to show
 *  @return {Editor} Editor instance, for chaining
 * 
 *  @example
 *    // Show a global message for a 'create' form
 *    editor.message( 'Add a new user to the database by completing the fields below' );
 *    editor.create( 'Add new user', {
 *      "label": "Submit",
 *      "fn": function () { this.submit(); }
 *    } );
 * 
 *  @example
 *    // Show a message for an individual field when a 'help' icon is clicked on
 *    $('#user_help').click( function () {
 *      editor.message( 'user', 'The user name is what the system user will login with' );
 *    } );
 */
Editor.prototype.message = function ( name, msg )
{
	if ( msg === undefined ) {
		// Global message
		this._message( this.dom.formInfo, name );
	}
	else {
		// Field message
		this.field( name ).message( msg );
	}

	return this;
};


/**
 * Get which mode of operation the Editor form is in
 *  @return {string} `create`, `edit`, `remove` or `null` if no active state.
 */
Editor.prototype.mode = function ( mode )
{
	if ( ! mode ) {
		return this.s.action;
	}
	
	if ( ! this.s.action ) {
		throw 'Not currently in an editing mode';
	}

	this.s.action = mode;
	return this;
};


/**
 * Get the modifier that was used to trigger the edit or delete action.
 *  @return {*} The identifier that was used for the editing / remove method
 *    called.
 */
Editor.prototype.modifier = function ()
{
	return this.s.modifier;
};


/**
 * Get the values from one or more fields, taking into account multiple data
 * points being edited at the same time.
 *
 * @param  {string|array} fieldNames A single field name or an array of field
 *   names.
 * @return {object} If a string is given as the first parameter an object that
 *   contains the value for each row being edited is returned. If an array is
 *   given, then the object has the field names as the parameter name and the
 *   value is the value object with values for each row being edited.
 */
Editor.prototype.multiGet = function ( fieldNames )
{
	var that = this;

	if ( fieldNames === undefined ) {
		fieldNames = this.fields();
	}

	if ( $.isArray( fieldNames ) ) {
		var out = {};

		$.each( fieldNames, function ( i, name ) {
			out[ name ] = that.field( name ).multiGet();
		} );

		return out;
	}

	// String
	return this.field( fieldNames ).multiGet();
};


/**
 * Set the values for one or more fields, taking into account multiple data
 * points being edited at the same time.
 *
 * @param  {object|string} fieldNames The name of the field to set, or an object
 *   with the field names as the parameters that contains the value object to
 *   set for each field.
 * @param  {*} [val] Value to set if first parameter is given as a string.
 *   Otherwise it is ignored.
 *  @return {Editor} Editor instance, for chaining
 */
Editor.prototype.multiSet = function ( fieldNames, val )
{
	var that = this;

	if ( $.isPlainObject( fieldNames ) && val === undefined ) {
		$.each( fieldNames, function ( name, value ) {
			that.field( name ).multiSet( value );
		} );
	}
	else {
		this.field( fieldNames ).multiSet( val );
	}

	return this;
};


/**
 * Get the container node for an individual field.
 *  @param {string|array} name The field name (from the `name` parameter given
 *   when originally setting up the field) to get the DOM node for.
 *  @return {node|array} Field container node
 * 
 *  @example
 *    // Dynamically add a class to a field's container
 *    $(editor.node( 'account_type' )).addClass( 'account' );
 */
Editor.prototype.node = function ( name )
{
	var that = this;

	if ( ! name ) {
		name = this.order();
	}

	return $.isArray( name ) ?
		$.map( name, function (n) {
			return that.field( n ).node();
		} ) :
		this.field( name ).node();
};


/**
 * Remove a bound event listener to the editor instance. This method provides a 
 * shorthand way of binding jQuery events that would be the same as writing 
 * `$(editor).off(...)` for convenience.
 *  @param {string} name Event name to remove the listeners for - event names are
 *    defined by {@link Editor}.
 *  @param {function} [fn] The function to remove. If not given, all functions which
 *    are assigned to the given event name will be removed.
 *  @return {Editor} Editor instance, for chaining
 *
 *  @example
 *    // Add an event to alert when the form is shown and then remove the listener
 *    // so it will only fire once
 *    editor.on( 'open', function () {
 *      alert('Form displayed!');
 *      editor.off( 'open' );
 *    } );
 */
Editor.prototype.off = function ( name, fn )
{
	$(this).off( this._eventName( name ), fn );

	return this;
};


/**
 * Listen for an event which is fired off by Editor when it performs certain
 * actions. This method provides a shorthand way of binding jQuery events that
 * would be the same as writing  `$(editor).on(...)` for convenience.
 *  @param {string} name Event name to add the listener for - event names are
 *    defined by {@link Editor}.
 *  @param {function} fn The function to run when the event is triggered.
 *  @return {Editor} Editor instance, for chaining
 *
 *  @example
 *    // Log events on the console when they occur
 *    editor.on( 'open', function () { console.log( 'Form opened' ); } );
 *    editor.on( 'close', function () { console.log( 'Form closed' ); } );
 *    editor.on( 'submit', function () { console.log( 'Form submitted' ); } );
 */
Editor.prototype.on = function ( name, fn )
{
	$(this).on( this._eventName( name ), fn );

	return this;
};


/**
 * Listen for a single event event which is fired off by Editor when it performs
 * certain actions. This method provides a shorthand way of binding jQuery
 * events that would be the same as writing  `$(editor).one(...)` for
 * convenience.
 *  @param {string} name Event name to add the listener for - event names are
 *    defined by {@link Editor}.
 *  @param {function} fn The function to run when the event is triggered.
 *  @return {Editor} Editor instance, for chaining
 */
Editor.prototype.one = function ( name, fn )
{
	$(this).one( this._eventName( name ), fn );

	return this;
};


/**
 * Display the main form editor to the end user in the web-browser.
 * 
 * Note that the `close()` method will close any of the three Editor form types
 * (main, bubble and inline), but this method will open only the main type.
 *  @return {Editor} Editor instance, for chaining
 * 
 *  @example
 *    // Build a 'create' form, but don't display it until some values have
 *    // been set. When done, then display the form.
 *    editor.create( 'Create user', {
 *      "label": "Submit",
 *      "fn": function () { this.submit(); }
 *    }, false );
 *    editor.set( 'name', 'Test user' );
 *    editor.set( 'access', 'Read only' );
 *    editor.open();
 */
Editor.prototype.open = function ()
{
	var that = this;

	// Insert the display elements in order
	this._displayReorder();

	// Define how to do a close
	this._closeReg( function ( submitComplete ) {
		that.s.displayController.close( that, function () {
			that._clearDynamicInfo();
		} );
	} );

	// Run the standard open with common events
	var ret = this._preopen( 'main' );
	if ( ! ret ) {
		return this;
	}

	this.s.displayController.open( this, this.dom.wrapper );
	this._focus(
		$.map( this.s.order, function (name) {
			return that.s.fields[ name ];
		} ),
		this.s.editOpts.focus
	);
	this._postopen( 'main' );

	return this;
};


/**
 * Get or set the ordering of fields, as they are displayed in the form. When used as
 * a getter, the field names are returned in an array, in their current order, and when
 * used as a setting you can alter the field ordering by passing in an array with all
 * field names in their new order.
 * 
 * Note that all fields *must* be included when reordering, and no additional fields can 
 * be added here (use {@link Editor#add} to add more fields). Finally, for setting the 
 * order, you can pass an array of the field names, or give the field names as individual
 * parameters (see examples below).
 *  @param {array|string} [set] Field order to set.
 *  @return {Editor} Editor instance, for chaining
 * 
 *  @example
 *    // Get field ordering
 *    var order = editor.order();
 * 
 *  @example
 *    // Set the field order
 *    var order = editor.order();
 *    order.unshift( order.pop() ); // move the last field into the first position
 *    editor.order( order );
 * 
 *  @example
 *    // Set the field order as arguments
 *    editor.order( "pupil", "grade", "dept", "exam-board" );
 *
 */
Editor.prototype.order = function ( set /*, ... */ )
{
	if ( !set ) {
		return this.s.order;
	}

	// Allow new layout to be passed in as arguments
	if ( arguments.length && ! $.isArray( set ) ) {
		set = Array.prototype.slice.call(arguments);
	}

	// Sanity check - array must exactly match the fields we have available
	if ( this.s.order.slice().sort().join('-') !== set.slice().sort().join('-') ) {
		throw "All fields, and no additional fields, must be provided for ordering.";
	}

	// Copy the new array into the order (so the reference is maintained)
	$.extend( this.s.order, set );

	this._displayReorder();

	return this;
};


/**
 * Remove (delete) entries from the table. The rows to remove are given as
 * either a single DOM node or an array of DOM nodes (including a jQuery
 * object).
 *  @param {node|array} items The row, or array of nodes, to delete
 *  @param {boolean} [show=true] Show the form or not.
 *  @return {Editor} Editor instance, for chaining
 * 
 *  @example
 *    // Delete a given row with a message to let the user know exactly what is
 *    // happening
 *    editor.message( "Are you sure you want to remove this row?" );
 *    editor.remove( row_to_delete, 'Delete row', {
 *      "label": "Confirm",
 *      "fn": function () { this.submit(); }
 *    } );
 * 
 *  @example
 *    // Delete the first row in a table without asking the user for confirmation
 *    editor.remove( '', $('#example tbody tr:eq(0)')[0], null, false );
 *    editor.submit();
 * 
 *  @example
 *    // Delete all rows in a table with a submit button
 *    editor.remove( $('#example tbody tr'), 'Delete all rows', {
 *      "label": "Delete all",
 *      "fn": function () { this.submit(); }
 *    } );
 */
Editor.prototype.remove = function ( items, arg1, arg2, arg3, arg4 )
{
	var that = this;

	// Some other field in inline edit mode?
	if ( this._tidy( function () { that.remove( items, arg1, arg2, arg3, arg4 ); } ) ) {
		return this;
	}

	// Allow a single row node to be passed in to remove, Can't use $.isArray
	// as we also allow array like objects to be passed in (API, jQuery)
	if ( items.length === undefined ) {
		items = [ items ];
	}

	var argOpts = this._crudArgs( arg1, arg2, arg3, arg4 );
	var editFields = this._dataSource( 'fields', items );

	this.s.action = "remove";
	this.s.modifier = items;
	this.s.editFields = editFields;
	this.dom.form.style.display = 'none';

	this._actionClass();

	this._event( 'initRemove', [
		_pluck( editFields, 'node' ),
		_pluck( editFields, 'data' ),
		items
	] );

	this._event( 'initMultiRemove', [
		editFields,
		items
	] );

	this._assembleMain();
	this._formOptions( argOpts.opts );

	argOpts.maybeOpen();

	var opts = this.s.editOpts;
	if ( opts.focus !== null ) {
		$('button', this.dom.buttons).eq( opts.focus ).focus();
	}

	return this;
};


/**
 * Set the value of a field
 *  @param {string|object} name The field name (from the `name` parameter given
 *    when originally setting up the field) to set the value of. If given as an
 *    object the object parameter name will be the value of the field to set and
 *    the value the value to set for the field.
 *  @param {*} [val] The value to set the field to. The format of the value will
 *    depend upon the field type. Not required if the first parameter is given
 *    as an object.
 *  @return {Editor} Editor instance, for chaining
 *
 *  @example
 *    // Set the values of a few fields before then automatically submitting the form
 *    editor.create( null, null, false );
 *    editor.set( 'name', 'Test user' );
 *    editor.set( 'access', 'Read only' );
 *    editor.submit();
 */
Editor.prototype.set = function ( set, val )
{
	var that = this;

	if ( ! $.isPlainObject( set ) ) {
		var o = {};
		o[ set ] = val;
		set = o;
	}

	$.each( set, function (n, v) {
		that.field( n ).set( v );
	} );

	return this;
};


/**
 * Show a field in the display that was previously hidden.
 *  @param {string|array} [names] The field name (from the `name` parameter
 *   given when originally setting up the field) to make visible, or an array of
 *   field names to make visible. If not given all fields are shown.
 *  @param {boolean} [animate=true] Animate if visible
 *  @return {Editor} Editor instance, for chaining
 * 
 *  @example
 *    // Shuffle the fields that are visible, hiding one field and making two
 *    // others visible before then showing the {@link Editor#create} record form.
 *    editor.hide( 'username' );
 *    editor.show( 'account_type' );
 *    editor.show( 'access_level' );
 *    editor.create( 'Add new user', {
 *      "label": "Save",
 *      "fn": function () { this.submit(); }
 *    } );
 *
 *  @example
 *    // Show all fields
 *    editor.show();
 */
Editor.prototype.show = function ( names, animate )
{
	var that = this;

	$.each( this._fieldNames( names ), function (i, n) {
		that.field( n ).show( animate );
	} );

	return this;
};


/**
 * Submit a form to the server for processing. The exact action performed will depend
 * on which of the methods {@link Editor#create}, {@link Editor#edit} or 
 * {@link Editor#remove} were called to prepare the form - regardless of which one is 
 * used, you call this method to submit data.
 *  @param {function} [successCallback] Callback function that is executed once the
 *    form has been successfully submitted to the server and no errors occurred.
 *  @param {function} [errorCallback] Callback function that is executed if the
 *    server reports an error due to the submission (this includes a JSON formatting
 *    error should the error return invalid JSON).
 *  @param {function} [formatdata] Callback function that is passed in the data
 *    that will be submitted to the server, allowing pre-formatting of the data,
 *    removal of data or adding of extra fields.
 *  @param {boolean} [hide=true] When the form is successfully submitted, by default
 *    the form display will be hidden - this option allows that to be overridden.
 *  @return {Editor} Editor instance, for chaining
 *
 *  @example
 *    // Submit data from a form button
 *    editor.create( 'Add new record', {
 *      "label": "Save",
 *      "fn": function () {
 *        this.submit();
 *      }
 *    } );
 *
 *  @example
 *    // Submit without showing the user the form
 *    editor.create( null, null, false );
 *    editor.submit();
 *
 *  @example
 *    // Provide success and error callback methods
 *    editor.create( 'Add new record', {
 *      "label": "Save",
 *      "fn": function () {
 *        this.submit( function () {
 *            alert( 'Form successfully submitted!' );
 *          }, function () {
 *            alert( 'Form  encountered an error :-(' );
 *          }
 *        );
 *      }
 *    } );
 *  
 *  @example
 *    // Add an extra field to the data
 *    editor.create( 'Add new record', {
 *      "label": "Save",
 *      "fn": function () {
 *        this.submit( null, null, function (data) {
 *          data.extra = "Extra information";
 *        } );
 *      }
 *    } );
 *
 *  @example
 *    // Don't hide the form immediately - change the title and then close the form
 *    // after a small amount of time
 *    editor.create( 'Add new record', {
 *      "label": "Save",
 *      "fn": function () {
 *        this.submit( 
 *          function () {
 *            var that = this;
 *            this.title( 'Data successfully added!' );
 *            setTimeout( function () {
 *              that.close();
 *            }, 1000 );
 *          },
 *          null,
 *          null,
 *          false
 *        );
 *      }
 *    } );
 *    
 */
Editor.prototype.submit = function ( successCallback, errorCallback, formatdata, hide )
{
	var
		that = this,
		fields = this.s.fields,
		errorFields = [],
		errorReady = 0,
		sent = false;

	if ( this.s.processing || ! this.s.action ) {
		return this;
	}
	this._processing( true );

	// If there are fields in error, we want to wait for the error notification
	// to be cleared before the form is submitted - errorFields tracks the
	// fields which are in the error state, while errorReady tracks those which
	// are ready to submit
	var send = function () {
		if ( errorFields.length !== errorReady || sent ) {
			return;
		}

		sent = true;
		that._submit( successCallback, errorCallback, formatdata, hide );
	};

	// Remove the global error (don't know if the form is still in an error
	// state!)
	this.error();

	// Count how many fields are in error
	$.each( fields, function ( name, field ) {
		if ( field.inError() ) {
			errorFields.push( name );
		}
	} );

	// Remove the error display
	$.each( errorFields, function ( i, name ) {
		fields[ name ].error('', function () {
			errorReady++;
			send();
		} );
	} );

	send();

	return this;
};


/**
 * Get / set the form template
 * @param  {string|node|jQuery|undefined} set If undefined, treat as a getter,
 *   otherwise set as the template - usually a selector.
 * @return {Editor|string|node|jQuery} Self is a setter, otherwise the template
 */
Editor.prototype.template = function ( set )
{
	if ( set === undefined ) {
		return this.s.template;
	}

	this.s.template = $(set);
	return this;
};


/**
 * Set the title of the form
 *  @param {string|function} title The title to give to the form
 *  @return {Editor} Editor instance, for chaining
 *
 *  @example
 *    // Create an edit display used the title, buttons and edit methods (note that
 *    // this is just an example, typically you would use the parameters of the edit
 *    // method to achieve this.
 *    editor.title( 'Edit record' );
 *    editor.buttons( {
 *      "label": "Update",
 *      "fn": function () { this.submit(); }
 *    } );
 *    editor.edit( TR_to_edit );
 *
 *  @example
 *    // Show a create form, with a timer for the duration that the form is open
 *    editor.create( 'Add new record - time on form: 0s', {
 *      "label": "Save",
 *      "fn": function () { this.submit(); }
 *    } );
 *    
 *    // Add an event to the editor to stop the timer when the display is removed
 *    var runTimer = true;
 *    var timer = 0;
 *    editor.on( 'close', function () {
 *      runTimer = false;
 *      editor.off( 'close' );
 *    } );
 *    // Start the timer running
 *    updateTitle();
 *
 *    // Local function to update the title once per second
 *    function updateTitle() {
 *      editor.title( 'Add new record - time on form: '+timer+'s' );
 *      timer++;
 *      if ( runTimer ) {
 *        setTimeout( function() {
 *          updateTitle();
 *        }, 1000 );
 *      }
 *    }
 */
Editor.prototype.title = function ( title )
{
	var header = $(this.dom.header).children( 'div.'+this.classes.header.content );

	if ( title === undefined ) {
		return header.html();
	}

	if ( typeof title === 'function' ) {
		title = title( this, new DataTable.Api(this.s.table) );
	}

	header.html( title );

	return this;
};


/**
 * Get or set the value of a specific field, or get the value of all fields in
 * the form.
 *
 * @param {string|array} [names] The field name(s) to get or set the value of.
 *   If not given, then the value of all fields will be obtained.
 * @param {*} [value] Value to set
 * @return {Editor|object|*} Editor instance, for chaining if used as a setter,
 *   an object containing the values of the requested fields if used as a
 *   getter with multiple fields requested, or the value of the requested field
 *   if a single field is requested.
 */
Editor.prototype.val = function ( field, value )
{
	if ( value !== undefined || $.isPlainObject( field ) ) {
		return this.set( field, value );
	}

	return this.get( field ); // field can be undefined to get all
};


/*
 * DataTables 1.10 API integration. Provides the ability to control basic Editor
 * aspects from the DataTables API. Full control does of course require use of
 * the Editor API though.
 */
var apiRegister = DataTable.Api.register;


function __getInst( api ) {
	var ctx = api.context[0];
	return ctx.oInit.editor || ctx._editor;
}

// Set sensible defaults for the editing options
function __setBasic( inst, opts, type, plural ) {
	if ( ! opts ) {
		opts = {};
	}

	if ( opts.buttons === undefined ) {
		opts.buttons = '_basic';
	}

	if ( opts.title === undefined ) {
		opts.title = inst.i18n[ type ].title;
	}

	if ( opts.message === undefined ) {
		if ( type === 'remove' ) {
			var confirm = inst.i18n[ type ].confirm;
			opts.message = plural!==1 ? confirm._.replace(/%d/, plural) : confirm['1'];
		}
		else {
			opts.message = '';
		}
	}

	return opts;
}


apiRegister( 'editor()', function () {
	return __getInst( this );
} );

// Row editing
apiRegister( 'row.create()', function ( opts ) {
	// main
	var inst = __getInst( this );
	inst.create( __setBasic( inst, opts, 'create' ) );
	return this;
} );

apiRegister( 'row().edit()', function ( opts ) {
	// main
	var inst = __getInst( this );
	inst.edit( this[0][0], __setBasic( inst, opts, 'edit' ) );
	return this;
} );

apiRegister( 'rows().edit()', function ( opts ) {
	// main
	var inst = __getInst( this );
	inst.edit( this[0], __setBasic( inst, opts, 'edit' ) );
	return this;
} );

apiRegister( 'row().delete()', function ( opts ) {
	// main
	var inst = __getInst( this );
	inst.remove( this[0][0], __setBasic( inst, opts, 'remove', 1 ) );
	return this;
} );

apiRegister( 'rows().delete()', function ( opts ) {
	// main
	var inst = __getInst( this );
	inst.remove( this[0], __setBasic( inst, opts, 'remove', this[0].length ) );
	return this;
} );

apiRegister( 'cell().edit()', function ( type, opts ) {
	// inline or bubble
	if ( ! type ) {
		type = 'inline';
	}
	else if ( $.isPlainObject( type ) ) {
		opts = type;
		type = 'inline';
	}

	__getInst( this )[ type ]( this[0][0], opts );
	return this;
} );

apiRegister( 'cells().edit()', function ( opts ) {
	// bubble only at the moment
	__getInst( this ).bubble( this[0], opts );
	return this;
} );

apiRegister( 'file()', _api_file );
apiRegister( 'files()', _api_files );

// Global listener for file information updates via DataTables' Ajax JSON
$(document).on( 'xhr.dt', function (e, ctx, json) {
	if ( e.namespace !== 'dt' ) {
		return;
	}

	if ( json && json.files ) {
		$.each( json.files, function ( name, files ) {
			Editor.files[ name ] = files;
		} );
	}
} );


/**
 * Common error message emitter. This method is not (yet) publicly documented on
 * the Editor site. It might be in future.
 *
 * @param  {string} msg Error message
 * @param  {int}    tn  Tech note link
 */
Editor.error = function ( msg, tn )
{
	throw tn ?
		msg +' For more information, please refer to https://datatables.net/tn/'+tn :
		msg;
};


/**
 * Obtain label / value pairs of data from a data source, be it an array or
 * object, for use in an input that requires label / value pairs such as
 * `select`, `radio` and `checkbox` inputs.
 *
 * A callback function is triggered for each label / value pair found, so the
 * caller can add it to the input as required.
 *
 * @static
 * @param {object|array} An object or array of data to iterate over getting the
 *     label / value pairs.
 * @param {object} props When an array of objects is passed in as the data
 *     source by default the label will be read from the `label` property and
 *     the value from the `value` property of the object. This option can alter
 *     that behaviour.
 * @param {function} fn Callback function. Takes three parameters: the label,
 *      the value and the iterator index.
 */
Editor.pairs = function ( data, props, fn )
{
	var i, ien, dataPoint;

	// Define default properties to read the data from if using an object.
	// The passed in `props` object and override.
	props = $.extend( {
		label: 'label',
		value: 'value'
	}, props );

	if ( $.isArray( data ) ) {
		// As an array, we iterate each item which can be an object or value
		for ( i=0, ien=data.length ; i<ien ; i++ ) {
			dataPoint = data[i];

			if ( $.isPlainObject( dataPoint ) ) {
				fn( 
					dataPoint[ props.value ] === undefined ?
						dataPoint[ props.label ] :
						dataPoint[ props.value ],
					dataPoint[ props.label ],
					i,
					dataPoint.attr // optional - can be undefined
				);
			}
			else {
				fn( dataPoint, dataPoint, i );
			}
		}
	}
	else {
		// As an object the key is the label and the value is the value
		i = 0;

		$.each( data, function ( key, val ) {
			fn( val, key, i );
			i++;
		} );
	}
};


/**
 * Make a string safe to use as a DOM ID. This is primarily for use by field
 * plug-in authors.
 *
 * @static
 * @param {string} String to make safe
 * @param {string} Safe string
 */
Editor.safeId = function ( id )
{
	return id.replace(/\./g, '-');
};


/**
 * Field specific upload method. This can be used to upload a file to the Editor
 * libraries. This method is not (yet) publicly documented on the Editor site.
 * It might be in future.
 *
 * @static
 * @param {Editor} editor The Editor instance operating on
 * @param {object} conf Field configuration object
 * @param {Files} files The file(s) to upload
 * @param {function} progressCallback Upload progress callback
 * @param {function} completeCallback Callback function for once the file has
 *     been uploaded
 */
Editor.upload = function ( editor, conf, files, progressCallback, completeCallback )
{
	var reader = new FileReader();
	var counter = 0;
	var ids = [];
	var generalError = 'A server error occurred while uploading the file';

	// Clear any existing errors, as the new upload might not be in error
	editor.error( conf.name, '' );

	progressCallback( conf, conf.fileReadText || "<i>Uploading file</i>" );

	reader.onload = function ( e ) {
		var data = new FormData();
		var ajax;

		data.append( 'action', 'upload' );
		data.append( 'uploadField', conf.name );
		data.append( 'upload', files[ counter ] );

		if ( conf.ajaxData ) {
			conf.ajaxData( data );
		}

		if ( conf.ajax ) {
			ajax = conf.ajax;
		}
		else if ( $.isPlainObject( editor.s.ajax ) ) {
			ajax = editor.s.ajax.upload ?
				editor.s.ajax.upload :
				editor.s.ajax;
		}
		else if ( typeof editor.s.ajax === 'string' ) {
			ajax = editor.s.ajax;
		}

		if ( ! ajax ) {
			throw 'No Ajax option specified for upload plug-in';
		}

		if ( typeof ajax === 'string' ) {
			ajax = { url: ajax };
		}

		// Use preSubmit to stop form submission during an upload, since the
		// value won't be known until that point.
		var submit = false;
		editor
			.on( 'preSubmit.DTE_Upload', function () {
				submit = true;
				return false;
			} );

		// Handle the case when the ajax data is given as a function
		if ( typeof ajax.data === 'function' ) {
			var d = {};
			var ret = ajax.data( d );

			// Allow the return to be used, or the object passed in
			if ( ret !== undefined && typeof ret !== 'string' ) {
				d = ret;
			}

			$.each( d, function ( key, value ) {
				data.append( key, value );
			} );
		}

		$.ajax( $.extend( {}, ajax, {
			type: 'post',
			data: data,
			dataType: 'json',
			contentType: false,
			processData: false,
			xhr: function () {
				var xhr = $.ajaxSettings.xhr();

				if ( xhr.upload ) {
					xhr.upload.onprogress = function ( e ) {
						if ( e.lengthComputable ) {
							var percent = (e.loaded/e.total*100).toFixed(0)+"%";

							progressCallback( conf, files.length === 1 ?
								percent :
								counter+':'+files.length+' '+percent
							);
						}
					};
					xhr.upload.onloadend = function ( e ) {
						progressCallback( conf, conf.processingText || 'Processing' );
					};
				}

				return xhr;
			},
			success: function ( json ) {
				editor.off( 'preSubmit.DTE_Upload' );
				editor._event( 'uploadXhrSuccess', [ conf.name, json ] );

				if ( json.fieldErrors && json.fieldErrors.length ) {
					var errors = json.fieldErrors;

					for ( var i=0, ien=errors.length ; i<ien ; i++ ) {
						editor.error( errors[i].name, errors[i].status );
					}
				}
				else if ( json.error ) {
					editor.error( json.error );
				}
				else if ( ! json.upload || ! json.upload.id ) {
					editor.error( conf.name, generalError );
				}
				else {
					if ( json.files ) {
						// Loop over the tables that are defined
						$.each( json.files, function ( table, files ) {
							if ( ! Editor.files[ table ] ) {
								Editor.files[ table ] = {};
							}
							$.extend( Editor.files[ table ], files );
						} );
					}

					ids.push( json.upload.id );

					if ( counter < files.length-1 ) {
						counter++;
						reader.readAsDataURL( files[counter] );
					}
					else {
						completeCallback.call( editor, ids );
						
						if ( submit ) {
							editor.submit();
						}
					}
				}

				progressCallback( conf );
			},
			error: function ( xhr ) {
				editor._event( 'uploadXhrError', [ conf.name, xhr ] );
				editor.error( conf.name, generalError );

				progressCallback( conf );
			}
		} ) );
	};

	reader.readAsDataURL( files[0] );
};
/**
 * Editor constructor - take the developer configuration and apply it to the instance.
 *  @param {object} init The initialisation options provided by the developer - see
 *    {@link Editor.defaults} for a full list of options.
 *  @private
 */
Editor.prototype._constructor = function(init) {
    init = $.extend(true, {}, Editor.defaults, init);
    this.s = $.extend(true, {}, Editor.models.settings, {
        table: init.domTable || init.table,
        dbTable: init.dbTable || null, // legacy
        ajaxUrl: init.ajaxUrl,
        ajax: init.ajax,
        idSrc: init.idSrc,
        dataSource: init.domTable || init.table ?
            Editor.dataSources.dataTable : Editor.dataSources.html,
        formOptions: init.formOptions,
        legacyAjax: init.legacyAjax,
        template: init.template ?
            $(init.template).detach() : null
    });
    this.classes = $.extend(true, {}, Editor.classes);
    this.i18n = init.i18n;

    // Increment the unique counter for the next instance
    Editor.models.settings.unique++;

    var that = this;
    var classes = this.classes;

    this.dom = {
        "wrapper": $(
            '<div class="' + classes.wrapper + '">' +
            '<div data-dte-e="processing" class="' + classes.processing.indicator + '"><span/></div>' +
            '<div data-dte-e="body" class="' + classes.body.wrapper + '">' +
            '<div data-dte-e="body_content" class="' + classes.body.content + '"/>' +
            '</div>' +
            '<div data-dte-e="foot" class="' + classes.footer.wrapper + '">' +
            '<div class="' + classes.footer.content + '"/>' +
            '</div>' +
            '</div>'
        )[0],
        "form": $(
            '<form data-dte-e="form" class="' + classes.form.tag + '">' +
            '<div data-dte-e="form_content" class="' + classes.form.content + '"/>' +
            '</form>'
        )[0],
        "formError": $('<div data-dte-e="form_error" class="' + classes.form.error + '"/>')[0],
        "formInfo": $('<div data-dte-e="form_info" class="' + classes.form.info + '"/>')[0],
        "header": $('<div data-dte-e="head" class="' + classes.header.wrapper + '"><div class="' + classes.header.content + '"/></div>')[0],
        "buttons": $('<div data-dte-e="form_buttons" class="' + classes.form.buttons + '"/>')[0]
    };

    // Customise the TableTools buttons with the i18n settings - worth noting that
    // this could easily be done outside the Editor instance, but this makes things
    // a bit easier to understand and more cohesive. Also worth noting that when
    // there are two or more Editor instances, the init sequence should be
    // Editor / DataTables, Editor / DataTables etc, since the value of these button
    // instances matter when you create the TableTools buttons for the DataTable.
    if ($.fn.dataTable.TableTools) {
        var ttButtons = $.fn.dataTable.TableTools.BUTTONS;
        var i18n = this.i18n;

        $.each(['create', 'edit', 'remove'], function(i, val) {
            ttButtons['editor_' + val].sButtonText = i18n[val].button;
        });
    }

    // Bind callback methods
    $.each(init.events, function(evt, fn) {
        that.on(evt, function() {
            // When giving events in the constructor the event argument was not
            // given in 1.2-, so we remove it here. This is solely for
            // backwards compatibility as the events in the initialisation are
            // not documented in 1.3+.
            var args = Array.prototype.slice.call(arguments);
            args.shift();
            fn.apply(that, args);
        });
    });

    // Cache the DOM nodes
    var dom = this.dom;
    var wrapper = dom.wrapper;
    dom.formContent = _editor_el('form_content', dom.form)[0];
    dom.footer = _editor_el('foot', wrapper)[0];
    dom.body = _editor_el('body', wrapper)[0];
    dom.bodyContent = _editor_el('body_content', wrapper)[0];
    dom.processing = _editor_el('processing', wrapper)[0];

    // Add any fields which are given on initialisation
    if (init.fields) {
        this.add(init.fields);
    }

    $(document)
        .on('init.dt.dte' + this.s.unique, function(e, settings, json) {
            // Attempt to attach to a DataTable automatically when the table is
            // initialised
            if (that.s.table && settings.nTable === $(that.s.table).get(0)) {
                settings._editor = that;
            }
        })
        .on('xhr.dt.dte' + this.s.unique, function(e, settings, json) {
            // Automatically update fields which have a field name defined in
            // the returned json - saves an `initComplete` for the user
            if (json && that.s.table && settings.nTable === $(that.s.table).get(0)) {
                that._optionsUpdate(json);
            }
        });

    // Prep the display controller
    try {
        this.s.displayController = Editor.display[init.display].init(this);
    }
    catch (e) {
        throw 'Cannot find display controller '+init.display;
    }

    this._event('initComplete', []);
};
/*global __inlineCounter*/

/**
 * Set the class on the form to relate to the action that is being performed.
 * This allows styling to be applied to the form to reflect the state that
 * it is in.
 *
 * @private
 */
Editor.prototype._actionClass = function ()
{
	var classesActions = this.classes.actions;
	var action = this.s.action;
	var wrapper = $(this.dom.wrapper);

	wrapper.removeClass( [classesActions.create, classesActions.edit, classesActions.remove].join(' ') );

	if ( action === "create" ) {
		wrapper.addClass( classesActions.create );
	}
	else if ( action === "edit" ) {
		wrapper.addClass( classesActions.edit );
	}
	else if ( action === "remove" ) {
		wrapper.addClass( classesActions.remove );
	}
};


/**
 * Create an Ajax request in the same style as DataTables 1.10, with full
 * backwards compatibility for Editor 1.2.
 *
 * @param  {object} data Data to submit
 * @param  {function} success Success callback
 * @param  {function} error Error callback
 * @param  {object} submitParams Submitted data
 * @private
 */
Editor.prototype._ajax = function ( data, success, error, submitParams )
{
	var that = this;
	var action = this.s.action;
	var thrown;
	var opts = {
		type:     'POST',
		dataType: 'json',
		data:     null,
		error:    [ function ( xhr, text, err ) {
			thrown = err;
		} ],
		success:  [],
		complete: [ function ( xhr, text ) {
			// Use `complete` rather than `success` so that all status codes are
			// caught and can return valid JSON (useful when working with REST
			// services).
			var json = null;

			if ( xhr.status === 204 || xhr.responseText === 'null' ) {
				json = {};
			}
			else {
				try {
					// jQuery 1.12 or newer for responseJSON, but its the only
					// way to get the JSON from a JSONP. So if you want to use
					// JSONP with Editor you have to use jQuery 1.12+.
					json = xhr.responseJSON ?
						xhr.responseJSON :
						$.parseJSON( xhr.responseText );
				}
				catch (e) {}
			}

			if ( $.isPlainObject( json ) || $.isArray( json ) ) {
				success( json, xhr.status >= 400, xhr );
			}
			else {
				error( xhr, text, thrown );
			}
		} ]
	};
	var a;
	var ajaxSrc = this.s.ajax || this.s.ajaxUrl;
	var id = action === 'edit' || action === 'remove' ?
		_pluck( this.s.editFields, 'idSrc' ) :
		null;

	if ( $.isArray( id ) ) {
		id = id.join(',');
	}

	// Get the correct object for rest style
	if ( $.isPlainObject( ajaxSrc ) && ajaxSrc[ action ] ) {
		ajaxSrc = ajaxSrc[ action ];
	}

	if ( $.isFunction( ajaxSrc ) ) {
		// As a function, execute it, passing in the required parameters
		var uri = null;
		var method = null;

		// If the old style ajaxSrc is given, we need to process it for
		// backwards compatibility with 1.2-. Unfortunate otherwise this would
		// be a very simply function!
		if ( this.s.ajaxUrl ) {
			var url = this.s.ajaxUrl;

			if ( url.create ) {
				uri = url[ action ];
			}

			if ( uri.indexOf(' ') !== -1 ) {
				a = uri.split(' ');
				method = a[0];
				uri = a[1];
			}

			uri = uri.replace( /_id_/, id );
		}
		
		ajaxSrc( method, uri, data, success, error );
		return;
	}
	else if ( typeof ajaxSrc === 'string' ) {
		// As a string it gives the URL. For backwards compatibility it can also
		// give the method.
		if ( ajaxSrc.indexOf(' ') !== -1 ) {
			a = ajaxSrc.split(' ');
			opts.type = a[0];
			opts.url = a[1];
		}
		else {
			opts.url = ajaxSrc;
		}
	}
	else {
		// As an object, we extend the Editor defaults - with the exception of
		// the error and complete functions which get added in so the user can
		// specify their own in addition to ours
		var optsCopy = $.extend( {}, ajaxSrc || {} );

		if ( optsCopy.complete ) {
			opts.complete.unshift( optsCopy.complete );
			delete optsCopy.complete;
		}

		if ( optsCopy.error ) {
			opts.error.unshift( optsCopy.error );
			delete optsCopy.error;
		}

		opts = $.extend( {}, opts, optsCopy );
	}

	// URL macros
	opts.url = opts.url.replace( /_id_/, id );

	// Data processing option like in DataTables
	if ( opts.data ) {
		var newData = $.isFunction( opts.data ) ?
			opts.data( data ) :  // fn can manipulate data or return an object
			opts.data;           // object or array to merge

		// If the function returned something, use that alone
		data = $.isFunction( opts.data ) && newData ?
			newData :
			$.extend( true, data, newData );
	}

	opts.data = data;

	// If a DELETE method is used there are a number of servers which will
	// reject the request if it has a body. So we need to append to the URL.
	//
	// http://stackoverflow.com/questions/15088955
	// http://bugs.jquery.com/ticket/11586
	if ( opts.type === 'DELETE' && (opts.deleteBody === undefined || opts.deleteBody === true) ) {
		var params = $.param( opts.data );

		opts.url += opts.url.indexOf('?') === -1 ?
			'?'+params :
			'&'+params;

		delete opts.data;
	}

	// Finally, make the ajax call
	$.ajax( opts );
};


/**
 * Create the DOM structure from the source elements for the main form.
 * This is required since the elements can be moved around for other form types
 * (bubble).
 *
 * @private
 */
Editor.prototype._assembleMain = function ()
{
	var dom = this.dom;

	$(dom.wrapper)
		.prepend( dom.header );

	$(dom.footer)
		.append( dom.formError )
		.append( dom.buttons );

	$(dom.bodyContent)
		.append( dom.formInfo )
		.append( dom.form );
};


/**
 * Blur the editing window. A blur is different from a close in that it might
 * cause either a close or the form to be submitted. A typical example of a
 * blur would be clicking on the background of the bubble or main editing forms
 * - i.e. it might be a close, or it might submit depending upon the
 * configuration, while a click on the close box is a very definite close.
 *
 * @private
 */
Editor.prototype._blur = function ()
{
	var opts = this.s.editOpts;
	var onBlur = opts.onBlur;

	if ( this._event( 'preBlur' ) === false ) {
		return;
	}

	if ( typeof onBlur === 'function' ) {
		onBlur( this );
	}
	else if ( onBlur === 'submit' ) {
		this.submit();
	}
	else if ( onBlur === 'close' ) {
		this._close();
	}
};


/**
 * Clear all of the information that might have been dynamically set while
 * the form was visible - specifically errors and dynamic messages
 *
 * @private
 */
Editor.prototype._clearDynamicInfo = function ()
{
	// Can be triggered due to a destroy if the editor is open
	if ( ! this.s ) {
		return;
	}

	var errorClass = this.classes.field.error;
	var fields = this.s.fields;

	$('div.'+errorClass, this.dom.wrapper).removeClass( errorClass );

	$.each( fields, function (name, field) {
		field
			.error('')
			.message('');
	} );

	this
		.error('')
		.message('');
};


/**
 * Close an editing display, firing callbacks and events as needed
 *
 * @param  {function} submitComplete Function to call after the preClose event
 * @private
 */
Editor.prototype._close = function ( submitComplete )
{
	// Allow preClose event to cancel the opening of the display
	if ( this._event( 'preClose' ) === false ) {
		return;
	}

	if ( this.s.closeCb ) {
		this.s.closeCb( submitComplete );
		this.s.closeCb = null;
	}

	if ( this.s.closeIcb ) {
		this.s.closeIcb();
		this.s.closeIcb = null;
	}

	// Remove focus control
	$('body').off( 'focus.editor-focus' );

	this.s.displayed = false;
	this._event( 'close' );
};


/**
 * Register a function to be called when the editing display is closed. This is
 * used by function that create the editing display to tidy up the display on
 * close - for example removing event handlers to prevent memory leaks.
 *
 * @param  {function} fn Function to call on close
 * @private
 */
Editor.prototype._closeReg = function ( fn )
{
	this.s.closeCb = fn;
};


/**
 * Argument shifting for the create(), edit() and remove() methods. In Editor
 * 1.3 the preferred form of calling those three methods is with just two
 * parameters (one in the case of create() - the id and the show flag), while in
 * previous versions four / three parameters could be passed in, including the
 * buttons and title options. In 1.3 the chaining API is preferred, but we want
 * to support the old form as well, so this function is provided to perform
 * that argument shifting, common to all three.
 *
 * @private
 */
Editor.prototype._crudArgs = function ( arg1, arg2, arg3, arg4 )
{
	var that = this;
	var title;
	var buttons;
	var show;
	var opts;

	if ( $.isPlainObject( arg1 ) ) {
		// Form options passed in as the first option
		opts = arg1;
	}
	else if ( typeof arg1 === 'boolean' ) {
		// Show / hide passed in as the first option - form options second
		show = arg1;
		opts = arg2; // can be undefined
	}
	else {
		// Old style arguments
		title = arg1; // can be undefined
		buttons = arg2; // can be undefined
		show = arg3; // can be undefined
		opts = arg4; // can be undefined
	}

	// If all undefined, then fall into here
	if ( show === undefined ) {
		show = true;
	}

	if ( title ) {
		that.title( title );
	}

	if ( buttons ) {
		that.buttons( buttons );
	}

	return {
		opts: $.extend( {}, this.s.formOptions.main, opts ),
		maybeOpen: function () {
			if ( show ) {
				that.open();
			}
		}
	};
};


/**
 * Execute the data source abstraction layer functions. This is simply a case
 * of executing the function with the Editor scope, passing in the remaining
 * parameters.
 *
 * @param {string) name Function name to execute
 * @private
 */
Editor.prototype._dataSource = function ( name /*, ... */ )
{
	// Remove the name from the arguments list, so the rest can be passed
	// straight into the field type
	var args = Array.prototype.slice.call( arguments );
	args.shift();

	var fn = this.s.dataSource[ name ];
	if ( fn ) {
		return fn.apply( this, args );
	}
};


/**
 * Insert the fields into the DOM, in the correct order
 *
 * @private
 */
Editor.prototype._displayReorder = function ( includeFields )
{
	var that = this;
	var formContent = $(this.dom.formContent);
	var fields = this.s.fields;
	var order = this.s.order;
	var template = this.s.template;
	var mode = this.s.mode || 'main';

	if ( includeFields ) {
		this.s.includeFields = includeFields;
	}
	else {
		includeFields = this.s.includeFields;
	}

	// Empty before adding in the required fields
	formContent.children().detach();

	$.each( order, function (i, fieldOrName) {
		var name = fieldOrName instanceof Editor.Field ?
			fieldOrName.name() :
			fieldOrName;

		if ( that._weakInArray( name, includeFields ) !== -1 ) {
			if ( template && mode === 'main' ) {
				template.find('editor-field[name="'+name+'"]').after(
					fields[ name ].node()
				);

				template.find( '[data-editor-template="'+name+'"]').append(
					fields[ name ].node()
				);
			}
			else {
				formContent.append( fields[ name ].node() );
			}
		}
	} );

	if ( template && mode === 'main' ) {
		template.appendTo( formContent );
	}

	this._event( 'displayOrder', [
		this.s.displayed,
		this.s.action,
		formContent
	] );
};


/**
 * Generic editing handler. This can be called by the three editing modes (main,
 * bubble and inline) to configure Editor for a row edit, and fire the required
 * events to ensure that the editing interfaces all provide a common API.
 *
 * @param {*} rows Identifier for the item(s) to be edited
 * @param {string} type Editing type - for the initEdit event
 * @private
 */
Editor.prototype._edit = function ( items, editFields, type )
{
	var that = this;
	var fields = this.s.fields;
	var usedFields = [];
	var includeInOrder;
	var editData = {};

	this.s.editFields = editFields;
	this.s.editData = editData;
	this.s.modifier = items;
	this.s.action = "edit";
	this.dom.form.style.display = 'block';
	this.s.mode = type;

	this._actionClass();

	// Setup the field values for editing
	$.each( fields, function ( name, field ) {
		field.multiReset();
		includeInOrder = false;
		editData[ name ] = {};

		$.each( editFields, function ( idSrc, edit ) {
			if ( edit.fields[ name ] ) {
				var val = field.valFromData( edit.data );

				// Save the set data values so we can decided in submit if data has changed
				editData[ name ][ idSrc ] = val;

				// Limit editing to only those fields selected if any are selected
				if ( ! edit.displayFields || edit.displayFields[ name ] ) {
					field.multiSet( idSrc, val !== undefined ?
						val :
						field.def()
					);

					includeInOrder = true;
				}
			}
		} );

		// If the field is used, then add it to the fields to be shown
		if ( field.multiIds().length !== 0 && includeInOrder ) {
			usedFields.push( name );
		}
	} );

	// Remove the fields that are not required from the display
	var currOrder = this.order().slice();

	for ( var i=currOrder.length-1 ; i >= 0 ; i-- ) {
		// Use `toString()` to convert numbers to strings, since usedFields
		// contains strings (object property names)
		if ( $.inArray( currOrder[i].toString(), usedFields ) === -1 ) {
			currOrder.splice( i, 1 );
		}
	}

	this._displayReorder( currOrder );

	// Events
	this._event( 'initEdit', [
		_pluck( editFields, 'node' )[0],
		_pluck( editFields, 'data' )[0],
		items,
		type
	] );

	this._event( 'initMultiEdit', [
		editFields,
		items,
		type
	] );
};


/**
 * Fire callback functions and trigger events.
 *
 * @param {string|array} trigger Name(s) of the jQuery custom event to trigger
 * @param {array} args Array of arguments to pass to the triggered event
 * @return {*} Return from the event
 * @private
 */
Editor.prototype._event = function ( trigger, args )
{
	if ( ! args ) {
		args = [];
	}

	// Allow an array to be passed in for the trigger to fire multiple events
	if ( $.isArray( trigger ) ) {
		for ( var i=0, ien=trigger.length ; i<ien ; i++ ) {
			this._event( trigger[i], args );
		}
	}
	else {
		var e = $.Event( trigger );

		$(this).triggerHandler( e, args );

		return e.result;
	}
};


/**
 * 'Modernise' event names, from the old style `on[A-Z]` names to camelCase.
 * This is done to provide backwards compatibility with Editor 1.2- event names.
 * The names themselves were updated for consistency with DataTables.
 *
 * @param {string} Event name to modernise
 * @return {string} String with new event name structure
 * @private
 */
Editor.prototype._eventName = function ( input )
{
	var name;
	var names = input.split( ' ' );

	for ( var i=0, ien=names.length ; i<ien ; i++ ) {
		name = names[i];

		// Strip the 'on' part and lowercase the first character
		var onStyle = name.match(/^on([A-Z])/);
		if ( onStyle ) {
			name = onStyle[1].toLowerCase() + name.substring( 3 );
		}

		names[i] = name;
	}

	return names.join( ' ' );
};


/**
 * Find a field from a DOM node. All children are searched.
 *
 * @param  {node} node DOM node to search for
 * @return {Field}     Field instance
 */
Editor.prototype._fieldFromNode = function ( node )
{
	var foundField = null;

	$.each( this.s.fields, function ( name, field ) {
		if ( $( field.node() ).find( node ).length ) {
			foundField = field;
		}
	} );

	return foundField;
};


/**
 * Convert a field name input parameter to an array of field names.
 *
 * Many of the API methods provide the ability to pass `undefined` a string or
 * array of strings to identify fields. This method harmonises that.
 *
 * @param  {array|string} [fieldNames] Field names to get
 * @return {array}                     Field names
 * @private
 */
Editor.prototype._fieldNames = function ( fieldNames )
{
	if ( fieldNames === undefined ) {
		return this.fields();
	}
	else if ( ! $.isArray( fieldNames ) ) {
		return [ fieldNames ];
	}

	return fieldNames;
};


/**
 * Focus on a field. Providing the logic to allow complex focus expressions
 *
 * @param {array} fields Array of Field instances or field names for the fields
 *     that are shown
 * @param {null|string|integer} focus Field identifier to focus on
 * @private
 */
Editor.prototype._focus = function ( fieldsIn, focus )
{
	var that = this;
	var field;
	var fields = $.map( fieldsIn, function ( fieldOrName ) {
		return typeof fieldOrName === 'string' ?
			that.s.fields[ fieldOrName ] :
			fieldOrName;
	} );

	if ( typeof focus === 'number' ) {
		field = fields[ focus ];
	}
	else if ( focus ) {
		if ( focus.indexOf( 'jq:' ) === 0 ) {
			field = $('div.DTE '+focus.replace(/^jq:/, ''));
		}
		else {
			field = this.s.fields[ focus ];
		}
	}

	this.s.setFocus = field;

	if ( field ) {
		field.focus();
	}
};


/**
 * Form options - common function so all editing methods can provide the same
 * basic options, DRY.
 *
 * @param {object} opts Editing options. See model.formOptions
 * @private
 */
Editor.prototype._formOptions = function ( opts )
{
	var that = this;
	var inlineCount = __inlineCounter++;
	var namespace = '.dteInline'+inlineCount;

	// Backwards compatibility with 1.4
	if ( opts.closeOnComplete !== undefined ) {
		opts.onComplete = opts.closeOnComplete ? 'close' : 'none';
	}

	if ( opts.submitOnBlur !== undefined ) {
		opts.onBlur = opts.submitOnBlur ? 'submit' : 'close';
	}

	if ( opts.submitOnReturn !== undefined ) {
		opts.onReturn = opts.submitOnReturn ? 'submit' : 'none';
	}

	if ( opts.blurOnBackground !== undefined ) {
		opts.onBackground = opts.blurOnBackground ? 'blur' : 'none';
	}

	this.s.editOpts = opts;

	// When submitting by Ajax we don't want to close a form that has been
	// opened during the ajax request, so we keep a count of the form opening
	this.s.editCount = inlineCount;

	if ( typeof opts.title === 'string' || typeof opts.title === 'function' ) {
		this.title( opts.title );
		opts.title = true;
	}

	if ( typeof opts.message === 'string' || typeof opts.message === 'function' ) {
		this.message( opts.message );
		opts.message = true;
	}

	if ( typeof opts.buttons !== 'boolean' ) {
		this.buttons( opts.buttons );
		opts.buttons = true;
	}

	$(document).on( 'keyup'+namespace, function ( e ) {
		var el = $(document.activeElement);

		if ( e.keyCode === 13 && that.s.displayed ) { // return
			var field = that._fieldFromNode( el );

			// Allow the field plug-in to say if we can submit or not
			if ( field && typeof field.canReturnSubmit === 'function' && field.canReturnSubmit( el ) ) {
				if ( opts.onReturn === 'submit' ) {
					e.preventDefault();
					that.submit();
				}
				else if ( typeof opts.onReturn === 'function' ) {
					e.preventDefault();
					opts.onReturn( that );
				}
			}
		}
		else if ( e.keyCode === 27 ) { // esc
			e.preventDefault();

			if ( typeof opts.onEsc === 'function' ) {
				opts.onEsc( that );
			}
			else if ( opts.onEsc === 'blur' ) {
				that.blur();
			}
			else if ( opts.onEsc === 'close' ) {
				that.close();
			}
			else if ( opts.onEsc === 'submit' ) {
				that.submit();
			}
		}
		else if ( el.parents('.DTE_Form_Buttons').length ) {
			if ( e.keyCode === 37 ) { // left
				el.prev( 'button' ).focus();
			}
			else if ( e.keyCode === 39 ) { // right
				el.next( 'button' ).focus();
			}
		}
	} );

	this.s.closeIcb = function () {
		$(document).off( 'keyup'+namespace );
	};

	return namespace;
};


/**
 * Convert from the 1.5+ data interchange format to the 1.4- format if suitable.
 *
 * @param  {string} direction 'send' or 'receive'
 * @param  {string} action    CRUD action
 * @param  {object} data      Data object to transform
 * @private
 */
Editor.prototype._legacyAjax = function ( direction, action, data )
{
	if ( ! this.s.legacyAjax || ! data ) {
		return;
	}

	if ( direction === 'send' ) {
		if ( action === 'create' || action === 'edit' ) {
			var id;

			$.each( data.data, function ( rowId, values ) {
				if ( id !== undefined ) {
					throw 'Editor: Multi-row editing is not supported by the legacy Ajax data format';
				}

				id = rowId;
			} );

			data.data = data.data[ id ];

			if ( action === 'edit' ) {
				data.id = id;
			}
		}
		else {
			data.id = $.map( data.data, function ( values, id ) {
				return id;
			} );

			delete data.data;
		}
	}
	else {
		if ( ! data.data && data.row ) {
			// 1.4 libraries retuned data in the `row` property
			data.data = [ data.row ];
		}
		else if ( ! data.data ) {
			// 1.4- allowed data not to be returned - 1.5 requires it
			data.data = [];
		}
	}
};


/**
 * Update the field options from a JSON data source
 *
 * @param  {object} json JSON object from the server
 * @private
 */
Editor.prototype._optionsUpdate = function ( json )
{
	var that = this;

	if ( json.options ) {
		$.each( this.s.fields, function (name, field) {
			if ( json.options[ name ] !== undefined ) {
				var fieldInst = that.field( name );

				if ( fieldInst && fieldInst.update ) {
					fieldInst.update( json.options[ name ] );
				}
			}
		} );
	}
};


/**
 * Show a message in the form. This can be used for error messages or dynamic
 * messages (information display) as the structure for each is basically the
 * same. This method will take into account if the form is visible or not - if
 * so then the message is shown with an effect for the end user, otherwise
 * it is just set immediately.
 *
 * @param {element} el The field display node to use
 * @param {string|function} msg The message to show
 * @private
 */
Editor.prototype._message = function ( el, msg )
{
	if ( typeof msg === 'function' ) {
		msg = msg( this, new DataTable.Api(this.s.table) );
	}

	el = $(el);

	if ( ! msg && this.s.displayed ) {
		// Clear the message with visual effect since the form is visible
		el
			.stop()
			.fadeOut( function () {
				el.html( '' );
			} );
	}
	else if ( ! msg ) {
		// Clear the message without visual effect
		el
			.html( '' )
			.css('display', 'none');
	}
	else if ( this.s.displayed ) {
		// Show the message with visual effect
		el
			.stop()
			.html( msg )
			.fadeIn();
	}
	else {
		// Show the message without visual effect
		el
			.html( msg )
			.css('display', 'block');
	}
};


/**
 * Update the multi-value information display to not show redundant information
 *
 * @private
 */
Editor.prototype._multiInfo = function ()
{
	var fields = this.s.fields;
	var include = this.s.includeFields;
	var show = true;
	var state;

	if ( ! include ) {
		return;
	}

	for ( var i=0, ien=include.length ; i<ien ; i++ ) {
		var field = fields[ include[i] ];
		var multiEditable = field.multiEditable();

		if ( field.isMultiValue() && multiEditable && show ) {
			// Multi-row editable. Only show first message
			state = true;
			show = false;
		}
		else if ( field.isMultiValue() && ! multiEditable ) {
			// Not multi-row editable. Always show message
			state = true;
		}
		else {
			state = false;
		}

		fields[ include[i] ].multiInfoShown( state );
	}
};


/**
 * Common display editing form method called by all editing methods after the
 * form has been configured and displayed. This is to ensure all fire the same
 * events.
 *
 * @param  {string} Editing type
 * @return {boolean} `true`
 * @private
 */
Editor.prototype._postopen = function ( type )
{
	var that = this;
	var focusCapture = this.s.displayController.captureFocus;
	if ( focusCapture === undefined ) {
		focusCapture = true;
	}

	$(this.dom.form)
		.off( 'submit.editor-internal' )
		.on( 'submit.editor-internal', function (e) {
			e.preventDefault();
		} );

	// Focus capture - when the Editor form is shown we capture the browser's
	// focus action. Without doing this is would result in the user being able
	// to control items under the Editor display - triggering actions that
	// shouldn't be possible while the editing is shown.
	if ( focusCapture && (type === 'main' || type === 'bubble') ) {
		$('body').on( 'focus.editor-focus', function () {
			if ( $(document.activeElement).parents('.DTE').length === 0 &&
			     $(document.activeElement).parents('.DTED').length === 0
			) {
				if ( that.s.setFocus ) {
					that.s.setFocus.focus();
				}
			}
		} );
	}

	this._multiInfo();

	this._event( 'open', [type, this.s.action] );

	return true;
};


/**
 * Common display editing form method called by all editing methods before the
 * form has been configured and displayed. This is to ensure all fire the same
 * events.
 *
 * @param  {string} Editing type
 * @return {boolean} `false` if the open is cancelled by the preOpen event,
 *   otherwise `true`
 * @private
 */
Editor.prototype._preopen = function ( type )
{
	// Allow preOpen event to cancel the opening of the display
	if ( this._event( 'preOpen', [type, this.s.action] ) === false ) {
		// Tidy- this would normally be done on close, but we never get that far
		this._clearDynamicInfo();
		this._event( 'cancelOpen', [type, this.s.action] );

		// inline and bubble methods cannot be opened using `open()`, they
		// have to be called again, so we need to clean up the event
		// listener added by _formOptions
		if ( (this.s.mode === 'inline' || this.s.mode === 'bubble') && this.s.closeIcb ) {
			this.s.closeIcb();
		}

		this.s.closeIcb = null;

		return false;
	}

	this.s.displayed = type;

	return true;
};


/**
 * Set the form into processing mode or take it out of processing mode. In
 * processing mode a processing indicator is shown and user interaction with the
 * form buttons is blocked
 *
 * @param {boolean} processing true if to go into processing mode and false if
 *   to come out of processing mode
 * @private
 */
Editor.prototype._processing = function ( processing )
{
	var procClass = this.classes.processing.active;

	$(['div.DTE', this.dom.wrapper]).toggleClass( procClass, processing );

	this.s.processing = processing;

	this._event( 'processing', [processing] );
};


/**
 * Submit a form to the server for processing. This is the private method that is used
 * by the 'submit' API method, which should always be called in preference to calling
 * this method directly.
 *
 * @param {function} [successCallback] Callback function that is executed once the
 *   form has been successfully submitted to the server and no errors occurred.
 * @param {function} [errorCallback] Callback function that is executed if the
 *   server reports an error due to the submission (this includes a JSON formatting
 *   error should the error return invalid JSON).
 * @param {function} [formatdata] Callback function that is passed in the data
 *   that will be submitted to the server, allowing pre-formatting of the data,
 *   removal of data or adding of extra fields.
 * @param {boolean} [hide=true] When the form is successfully submitted, by default
 *   the form display will be hidden - this option allows that to be overridden.
 * @private
 */
Editor.prototype._submit = function ( successCallback, errorCallback, formatdata, hide )
{
	var that = this;
	var i, iLen, eventRet, errorNodes;
	var changed = false, allData = {}, changedData = {};
	var setBuilder =  DataTable.ext.oApi._fnSetObjectDataFn;
	var dataSource = this.s.dataSource;
	var fields = this.s.fields;
	var editCount = this.s.editCount;
	var modifier = this.s.modifier;
	var editFields = this.s.editFields;
	var editData = this.s.editData;
	var opts = this.s.editOpts;
	var changedSubmit = opts.submit;
	var submitParamsLocal;
	
	if ( this._event( 'initSubmit', [this.s.action] ) === false ) {
		this._processing( false );
		return;
	}

	// After initSubmit to allow `mode()` to be used as a setter
	var action = this.s.action;
	var submitParams = {
		"action": action,
		"data": {}
	};

	// For backwards compatibility
	if ( this.s.dbTable ) {
		submitParams.table = this.s.dbTable;
	}

	// Gather the data that is to be submitted
	if ( action === "create" || action === "edit" ) {
		$.each( editFields, function ( idSrc, edit ) {
			var allRowData = {};
			var changedRowData = {};

			$.each( fields, function (name, field) {
				if ( edit.fields[ name ] ) {
					var multiGet = field.multiGet();
					var builder = setBuilder( name );

					// If it wasn't an edit field, we still need to get the original
					// data, so we can submit it if `all` or `allIfChanged`
					if ( multiGet[ idSrc ] === undefined ) {
						var originalVal = field.valFromData( edit.data );
						builder( allRowData, originalVal );

						return;
					}

					var value = multiGet[ idSrc ];
					var manyBuilder = $.isArray( value ) && name.indexOf('[]') !== -1 ?
						setBuilder( name.replace(/\[.*$/,'')+'-many-count' ) :
						null;

					builder( allRowData, value );

					// We need to tell the server-side if an array submission
					// actually has no elements so it knows if the array was
					// being submitted or not (since otherwise it doesn't know
					// if the array was empty, or just not being submitted)
					if ( manyBuilder ) {
						manyBuilder( allRowData, value.length );
					}

					// Build a changed object for if that is the selected data
					// type
					if ( action === 'edit' && (!editData[ name ] || ! field.compare( value, editData[ name ][ idSrc ]) ) ) {
						builder( changedRowData, value );
						changed = true;

						if ( manyBuilder ) {
							manyBuilder( changedRowData, value.length );
						}
					}
				}
			} );

			if ( ! $.isEmptyObject( allRowData ) ) {
				allData[ idSrc ] = allRowData;
			}

			if ( ! $.isEmptyObject( changedRowData ) ) {
				changedData[ idSrc ] = changedRowData;
			}
		} );

		// Decide what data to submit to the server for edit (create is all, always)
		if ( action === 'create' || changedSubmit === 'all' || (changedSubmit === 'allIfChanged' && changed) ) {
			submitParams.data = allData;
		}
		else if ( changedSubmit === 'changed' && changed ) {
			submitParams.data = changedData;
		}
		else {
			// Nothing to submit
			this.s.action = null;

			if ( opts.onComplete === 'close' && (hide === undefined || hide) ) {
				this._close( false );
			}
			else if ( typeof opts.onComplete === 'function' ) {
				opts.onComplete( this );
			}

			if ( successCallback ) {
				successCallback.call( this );
			}

			this._processing( false );
			this._event( 'submitComplete' );
			return;
		}
	}
	else if ( action === "remove" ) {
		$.each( editFields, function ( idSrc, edit ) {
			submitParams.data[ idSrc ] = edit.data;
		} );
	}

	this._legacyAjax( 'send', action, submitParams );

	// Local copy of the submit parameters, needed for the data lib prep since
	// the preSubmit can modify the format and we need to know what the format is
	submitParamsLocal = $.extend( true, {}, submitParams );

	// Allow the data to be submitted to the server to be preprocessed by callback
	// and event functions
	if ( formatdata ) {
		formatdata( submitParams );
	}
	if ( this._event( 'preSubmit', [submitParams, action] ) === false ) {
		this._processing( false );
		return;
	}

	// Submit to the server (or whatever method is defined in the settings)
	var submitWire = this.s.ajax || this.s.ajaxUrl ?
		this._ajax :
		this._submitTable;

	submitWire.call(
		this,
		submitParams,
		function (json, notGood, xhr) {
			that._submitSuccess(
				json, notGood, submitParams, submitParamsLocal, that.s.action,
				editCount, hide, successCallback, errorCallback, xhr
			);
		},
		function (xhr, err, thrown) {
			that._submitError( xhr, err, thrown, errorCallback, submitParams, that.s.action );
		},
		submitParams
	);
};


/**
 * Save submitted data without an Ajax request. This will write to a local
 * table only - not saving it permanently, but rather using the DataTable itself
 * as a data store.
 *
 * @param  {object} data Data to submit
 * @param  {function} success Success callback
 * @param  {function} error Error callback
 * @param  {object} submitParams Submitted data
 * @private
 */
Editor.prototype._submitTable = function ( data, success, error, submitParams )
{
	var that = this;
	var action = data.action;
	var out = { data: [] };
	var idGet = DataTable.ext.oApi._fnGetObjectDataFn( this.s.idSrc );
	var idSet = DataTable.ext.oApi._fnSetObjectDataFn( this.s.idSrc );

	// Nothing required for remove - create and edit get a copy of the data
	if ( action !== 'remove' ) {
		var originalData = this._dataSource( 'fields', this.modifier() );

		$.each( data.data, function ( key, vals ) {
			var toSave;

			// Get the original row's data, so we can modify it with new values.
			// This allows Editor to not need to submit all fields
			if ( action === 'edit' ) {
				var rowData = originalData[ key ].data;
				toSave = $.extend( true, {}, rowData, vals );
			}
			else {
				toSave = $.extend( true, {}, vals );
			}

			// If create and there isn't an id for the new row, create
			// one. An id could be creased by `preSubmit`
			if ( action === 'create' && idGet( toSave ) === undefined ) {
				idSet( toSave, +new Date() +''+ key );
			}
			else {
				idSet( toSave, key );
			}

			out.data.push( toSave );
		} );
	}

	success( out );
};


/**
 * Submit success callback function
 * @param  {object} json                Payload
 * @param  {bool} notGood               True if the returned status code was
 *   >=400 (i.e. processing failed). This is called `notGood` rather than
 *   `success` since the request was successfully processed, just not written to
 *   the db. It is also inverted from "good" to make it optional when overriding
 *   the `ajax` function.
 * @param  {object} submitParams        Submitted data
 * @param  {object} submitParamsLocal   Unmodified copy of submitted data
 *   (before it could be modified by the user)
 * @param  {string} action              CRUD action being taken
 * @param  {int} editCount              Protection against async errors
 * @param  {bool} hide                  Hide the form flag
 * @param  {function} successCallback   Success callback
 * @param  {function} errorCallback     Error callback
 * @private
 */
Editor.prototype._submitSuccess = function ( json, notGood, submitParams, submitParamsLocal, action, editCount, hide, successCallback, errorCallback, xhr )
{
	var that = this;
	var setData;
	var fields = this.s.fields;
	var opts = this.s.editOpts;
	var modifier = this.s.modifier;

	this._legacyAjax( 'receive', action, json );
	this._event( 'postSubmit', [json, submitParams, action, xhr] );

	if ( !json.error ) {
		json.error = "";
	}
	if ( !json.fieldErrors ) {
		json.fieldErrors = [];
	}

	if ( notGood || json.error || json.fieldErrors.length ) {
		// Global form error
		this.error( json.error );

		// Field specific errors
		$.each( json.fieldErrors, function (i, err) {
			var field = fields[ err.name ];

			field.error( err.status || "Error" );

			if ( i === 0 ) {
				if ( opts.onFieldError === 'focus' ) {
					// Scroll the display to the first error and focus
					$(that.dom.bodyContent, that.s.wrapper).animate( {
						"scrollTop": $(field.node()).position().top
					}, 500 );

					field.focus();
				}
				else if ( typeof opts.onFieldError === 'function' ) {
					opts.onFieldError( that, err );
				}
			}
		} );

		this._event( 'submitUnsuccessful', [json] );
		if ( errorCallback ) {
			errorCallback.call( that, json );
		}
	}
	else {
		// Create a data store that the data source can use, which is
		// unique to this action
		var store = {};

		if ( json.data && (action === "create"  || action === "edit") ) {
			this._dataSource( 'prep', action, modifier, submitParamsLocal, json, store );

			for ( var i=0 ; i<json.data.length ; i++ ) {
				setData = json.data[ i ];
				this._event( 'setData', [json, setData, action] ); // legacy

				if ( action === "create" ) {
					// New row was created to add it to the DT
					this._event( 'preCreate', [json, setData] );
					this._dataSource( 'create', fields, setData, store );
					this._event( ['create', 'postCreate'], [json, setData] );
				}
				else if ( action === "edit" ) {
					// Row was updated, so tell the DT
					this._event( 'preEdit', [json, setData] );
					this._dataSource( 'edit', modifier, fields, setData, store );
					this._event( ['edit', 'postEdit'], [json, setData] );
				}
			}

			this._dataSource( 'commit', action, modifier, json.data, store );
		}
		else if ( action === "remove" ) {
			this._dataSource( 'prep', action, modifier, submitParamsLocal, json, store );

			// Remove the rows given and then redraw the table
			this._event( 'preRemove', [json] );
			this._dataSource( 'remove', modifier, fields, store );
			this._event( ['remove', 'postRemove'], [json] );

			this._dataSource( 'commit', action, modifier, json.data, store );
		}

		// Submission complete
		if ( editCount === this.s.editCount ) {
			this.s.action = null;

			if ( opts.onComplete === 'close' && (hide === undefined || hide) ) {
				// If no data returned, then treat as not complete
				this._close( json.data ? true : false );
			}
			else if ( typeof opts.onComplete === 'function' ) {
				opts.onComplete( this );
			}
		}

		// All done - fire off the callbacks and events
		if ( successCallback ) {
			successCallback.call( that, json );
		}
		this._event( 'submitSuccess', [json, setData, action] );
	}

	this._processing( false );
	this._event( 'submitComplete', [json, setData, action] );
};


/**
 * Submit error callback function
 * @private
 */
Editor.prototype._submitError = function ( xhr, err, thrown, errorCallback, submitParams, action )
{
	this._event( 'postSubmit', [null, submitParams, action, xhr] );

	this.error( this.i18n.error.system );
	this._processing( false );

	if ( errorCallback ) {
		errorCallback.call( this, xhr, err, thrown );
	}

	this._event( ['submitError', 'submitComplete'], [xhr, err, thrown, submitParams] );
};


/**
 * Check to see if the form needs to be tidied before a new action can be performed.
 * This includes if the from is currently processing an old action and if it
 * is inline editing.
 *
 * @param {function} fn Callback function
 * @returns {boolean} `true` if was in inline mode, `false` otherwise
 * @private
 */
Editor.prototype._tidy = function ( fn )
{
	var that = this;
	var dt = this.s.table ?
		new $.fn.dataTable.Api( this.s.table ) :
		null;

	var ssp = false;
	if ( dt ) {
		ssp = dt.settings()[0].oFeatures.bServerSide;
	}

	if ( this.s.processing ) {
		// If currently processing, wait until the action is complete
		this.one( 'submitComplete', function () {
			// If server-side processing is being used in DataTables, first
			// check that we are still processing (might not be if nothing was
			// submitted) and then wait for the draw to finished
			if ( ssp ) {
				dt.one( 'draw', fn );
			}
			else {
				setTimeout( function () {
					fn();
				}, 10 );
			}
		} );

		return true;
	}
	else if ( this.display() === 'inline' || this.display() === 'bubble' ) {
		// If there is an inline edit box, it needs to be tidied
		this
			.one( 'close', function () {
				// On close if processing then we need to wait for the submit to
				// complete before running the callback as onBlur was set to
				// submit
				if ( ! that.s.processing ) {
					// IE needs a small timeout, otherwise it may not focus on a
					// field if one already has focus
					setTimeout( function () {
						fn();
					}, 10 );
				}
				else {
					// Need to wait for the submit to finish
					that.one( 'submitComplete', function ( e, json ) {
						// If SSP then need to wait for the draw
						if ( ssp && json ) {
							dt.one( 'draw', fn );
						}
						else {
							setTimeout( function () {
								fn();
							}, 10 );
						}
					} );
				}
			} )
			.blur();

		return true;
	}

	return false;
};

/**
 * Same as $.inArray but with weak type checking
 * @param {any} name Value to look for in the array
 * @param {array} arr Array to scan through
 * @returns {number} -1 if not found, index otherwise
 */
Editor.prototype._weakInArray = function ( name, arr )
{
	for ( var i=0, ien=arr.length ; i<ien ; i++ ) {
		if ( name == arr[i] ) {
			return i;
		}
	}

	return -1;
};

/*
 * Defaults
 */


// Dev node - although this file is held in the models directory (because it
// really is a model, it is assigned to Editor.defaults for easy
// and sensible access to set the defaults for Editor.

/**
 * Initialisation options that can be given to Editor at initialisation time.
 *  @namespace
 */
Editor.defaults = {
	/**
	 * jQuery selector that can be used to identify the table you wish to apply
	 * this editor instance to.
	 *
	 * In previous versions of Editor (1.2 and earlier), this parameter was
	 * called `table`. The name has been altered in 1.3+ to simplify the
	 * initialisation. This is a backwards compatible change - if you pass in
	 * a `table` option it will be used.
	 *  @type string
	 *  @default <i>Empty string</i>
	 *
	 *  @example
	 *    $(document).ready(function() {
	 *      var editor = new $.fn.Editor( {
	 *        "ajax": "php/index.php",
	 *        "table": "#example"
	 *      } );
	 *    } );
	 */
	"table": null,

	/**
	 * The URL, or collection of URLs when using a REST interface, which will accept 
	 * the data for the create, edit and remove functions. The target script / program
	 * must accept data in the format defined by Editor and return the expected JSON as
	 * required by Editor. When given as an object, the `create`, `edit` and `remove`
	 * properties should be defined, each being the URL to send the data to for that
	 * action. When used as an object, the string `_id_` will be replaced for the edit
	 * and remove actions, allowing a URL to be dynamically created for those actions.
	 *  @type string|object
	 *  @default <i>Empty string</i>
	 *  @deprecated This option has been deprecated in favour of the `ajax` option.
	 *    It can still be used, but it is recommended that you use the `ajax` option
	 *    which provides all of the abilities of this old option and more.
	 */
	"ajaxUrl": null,

	/**
	 * Fields to initialise the form with - see {@link Editor.models.field} for
	 * a full list of the options available to each field. Note that if fields are not 
	 * added to the form at initialisation time using this option, they can be added using
	 * the {@link Editor#add} API method.
	 *  @type array
	 *  @default []
	 *
	 *  @example
	 *    $(document).ready(function() {
	 *      var editor = new $.fn.Editor( {
	 *        "ajax": "php/index.php",
	 *        "table": "#example",
	 *        "fields": [ {
	 *            "label": "User name:",
	 *            "name": "username"
	 *          }
	 *          // More fields would typically be added here!
	 *        } ]
	 *      } );
	 *    } );
	 */
	"fields": [],

	/**
	 * The display controller for the form. The form itself is just a collection of
	 * DOM elements which require a display container. This display controller allows
	 * the visual appearance of the form to be significantly altered without major
	 * alterations to the Editor code. There are two display controllers built into
	 * Editor *lightbox* and *envelope*. The value of this property will
	 * be used to access the display controller defined in {@link Editor.display}
	 * for the given name. Additional display controllers can be added by adding objects
	 * to that object, through extending the displayController model:
	 * {@link Editor.models.displayController}.
	 *  @type string
	 *  @default lightbox
	 *
	 *  @example
	 *    $(document).ready(function() {
	 *      var editor = new $.fn.Editor( {
	 *        "ajax": "php/index.php",
	 *        "table": "#example",
	 *        "display": 'envelope'
	 *      } );
	 *    } );
	 */
	"display": 'lightbox',

	/**
	 * Control how the Ajax call to update data on the server.
	 *
	 * This option matches the `dt-init ajax` option in that is can be provided
	 * in one of three different ways:
	 *
	 * * string - As a string, the value given is used as the url to target
	 *   the Ajax request to, using the default Editor Ajax options. Note that
	 *   for backwards compatibility you can use the form "METHOD URL" - for
	 *   example: `"PUT api/users"`, although it is recommended you use the
	 *   object form described below.
	 * * object - As an object, the `ajax` property has two forms:
	 *   * Used to extend and override the default Ajax options that Editor
	 *     uses. This can be very useful for adding extra data for example, or
	 *     changing the HTTP request type.
	 *   * With `create`, `edit` and `remove` properties, Editor will use the
	 *     option for the action that it is taking, which can be useful for
	 *     REST style interfaces. The value of each property can be a string,
	 *     object or function, using exactly the same options as the main `ajax`
	 *     option. All three options must be defined if this form is to be used.
	 * * function - As a function this gives complete control over the method
	 *   used to update the server (if indeed a server is being used!). For
	 *   example, you could use a different data store such as localStorage,
	 *   Firebase or route the data through a web-socket.
	 *
	 *  @example
	 *    // As a string - all actions are submitted to this URI as POST requests
	 *    $(document).ready(function() {
	 *      var editor = new $.fn.Editor( {
	 *        "ajax": 'php/index.php',
	 *        "table": "#example"
	 *      } );
	 *    } );
	 *
	 *  @example
	 *    // As an object - using GET rather than POST
	 *    $(document).ready(function() {
	 *      var editor = new $.fn.Editor( {
	 *        "ajax": {
	 *          "type": 'GET',
	 *          "url": 'php/index.php
	 *        },
	 *        "table": "#example"
	 *      } );
	 *    } );
	 *
	 *  @example
	 *    // As an object - each action is submitted to a different URI as POST requests
	 *    $(document).ready(function() {
	 *      var editor = new $.fn.Editor( {
	 *        "ajax": {
	 *          "create": "/rest/user/create",
	 *          "edit":   "/rest/user/_id_/edit",
	 *          "remove": "/rest/user/_id_/delete"
	 *        },
	 *        "table": "#example"
	 *      } );
	 *    } );
	 *
	 *  @example
	 *    // As an object - with different HTTP methods for each action
	 *    $(document).ready(function() {
	 *      var editor = new $.fn.Editor( {
	 *        "ajax": {
	 *          "create": {
	 *          	type: 'POST',
	 *          	url:  '/rest/user/create'
	 *          },
	 *          "edit": {
	 *          	type: 'PUT',
	 *          	url:  '/rest/user/edit/_id_'
	 *          },
	 *          "remove": {
	 *          	type: 'DELETE',
	 *          	url:  '/rest/user/delete'
	 *          }
	 *        },
	 *        "table": "#example"
	 *      } );
	 *    } );
	 *
	 *    // As a function - Making a custom `$.ajax` call
	 *    $(document).ready(function() {
	 *      var editor = new $.fn.Editor( {
	 *        "ajax": "php/index.php",
	 *        "table": "#example",
	 *        "ajax": function ( method, url, data, successCallback, errorCallback ) {
	 *          $.ajax( {
	 *            "type": method,
	 *            "url":  url,
	 *            "data": data,
	 *            "dataType": "json",
	 *            "success": function (json) {
	 *              successCallback( json );
	 *            },
	 *            "error": function (xhr, error, thrown) {
	 *              errorCallback( xhr, error, thrown );
	 *            }
	 *          } );
	 *        }
	 *      } );
	 *    } );
	 */
	"ajax": null,

	/**
	 * JSON property from which to read / write the row's ID property (i.e. its
	 * unique column index that identifies the row to the database). By default
	 * Editor will use the `DT_RowId` property from the data source object
	 * (DataTable's magic property to set the DOM id for the row).
	 *
	 * If you want to read a parameter from the data source object instead of
	 * using `DT_RowId`, set this option to the property name to use.
	 *
	 * Like other data source options the `srcId` option can be given in dotted
	 * object notation to read nested objects.
	 *  @type null|string
	 *  @default DT_RowId
	 *
	 *  @example
	 *    // Using a data source such as:
	 *    // { "id":12, "browser":"Chrome", ... }
	 *    $(document).ready(function() {
	 *      var editor = new $.fn.Editor( {
	 *        "ajax": "php/index.php",
	 *        "table": "#example",
	 *        "idSrc": "id"
	 *      } );
	 *    } );
	 */
	"idSrc": 'DT_RowId',

	/**
	 * Events / callbacks - event handlers can be assigned as an individual function
	 * during initialisation using the parameters in this name space. The names, and
	 * the parameters passed to each callback match their event equivalent in the
	 * {@link Editor} object.
	 *  @namespace
	 *  @deprecated Since 1.3. Use the `on()` API method instead. Note that events
	 *    passed in do still operate as they did in 1.2- but are no longer
	 *    individually documented.
	 */
	"events": {},

	/**
	 * Internationalisation options for Editor. All client-side strings that the
	 * end user can see in the interface presented by Editor can be modified here.
	 *
	 * You may also wish to refer to the <a href="http://datatables.net/usage/i18n">
	 * DataTables internationalisation options</a> to provide a fully language 
	 * customised table interface.
	 *  @namespace
	 *
	 *  @example
	 *    // Set the 'create' button text. All other strings used are the
	 *    // default values.
	 *    var editor = new $.fn.Editor( {
	 *      "ajax": "data/source",
	 *      "table": "#example",
	 *      "i18n": {
	 *        "create": {
	 *          "button": "New user"
	 *        }
	 *      }
	 *    } );
	 *
	 *  @example
	 *    // Set the submit text for all three actions
	 *    var editor = new $.fn.Editor( {
	 *      "ajax": "data/source",
	 *      "table": "#example",
	 *      "i18n": {
	 *        "create": {
	 *          "submit": "Create new user"
	 *        },
	 *        "edit": {
	 *          "submit": "Update user"
	 *        },
	 *        "remove": {
	 *          "submit": "Remove user"
	 *        }
	 *      }
	 *    } );
	 */
	"i18n": {
		/**
		 * Strings used when working with the Editor 'create' action (creating new
		 * records).
		 *  @namespace
		 */
		"create": {
			/**
			 * TableTools button text
			 *  @type string
			 *  @default New
			 */
			"button": "New",

			/**
			 * Display container title (when showing the editor display)
			 *  @type string
			 *  @default Create new entry
			 */
			"title":  "Create new entry",

			/**
			 * Submit button text
			 *  @type string
			 *  @default Create
			 */
			"submit": "Create"
		},

		/**
		 * Strings used when working with the Editor 'edit' action (editing existing
		 * records).
		 *  @namespace
		 */
		"edit": {
			/**
			 * TableTools button text
			 *  @type string
			 *  @default Edit
			 */
			"button": "Edit",

			/**
			 * Display container title (when showing the editor display)
			 *  @type string
			 *  @default Edit entry
			 */
			"title":  "Edit entry",

			/**
			 * Submit button text
			 *  @type string
			 *  @default Update
			 */
			"submit": "Update"
		},

		/**
		 * Strings used when working with the Editor 'delete' action (deleting 
		 * existing records).
		 *  @namespace
		 */
		"remove": {
			/**
			 * TableTools button text
			 *  @type string
			 *  @default Delete
			 */
			"button": "Delete",

			/**
			 * Display container title (when showing the editor display)
			 *  @type string
			 *  @default Delete
			 */
			"title":  "Delete",

			/**
			 * Submit button text
			 *  @type string
			 *  @default Delete
			 */
			"submit": "Delete",

			/**
			 * Deletion confirmation message.
			 *
			 * As Editor has the ability to delete either a single or multiple rows
			 * at a time, this option can be given as either a string (which will be
			 * used regardless of how many records are selected) or as an object 
			 * where the property "_" will be used (with %d substituted for the number
			 * of records to be deleted) as the delete message, unless there is a
			 * key with the number of records to be deleted. This allows Editor
			 * to consider the different pluralisation characteristics of different
			 * languages.
			 *  @type object|string
			 *  @default Are you sure you wish to delete %d rows?
			 *
			 *  @example
			 *    // String - no plural consideration
			 *    var editor = new $.fn.Editor( {
			 *      "ajax": "data/source",
			 *      "table": "#example",
			 *      "i18n": {
			 *        "remove": {
			 *          "confirm": "Are you sure you wish to delete %d record(s)?"
			 *        }
			 *      }
			 *    } );
			 *
			 *  @example
			 *    // Basic 1 (singular) or _ (plural)
			 *    var editor = new $.fn.Editor( {
			 *      "ajax": "data/source",
			 *      "table": "#example",
			 *      "i18n": {
			 *        "remove": {
			 *          "confirm": {
			 *            "_": "Confirm deletion of %d records.",
			 *            "1": "Confirm deletion of record."
			 *        }
			 *      }
			 *    } );
			 *
			 *  @example
			 *    // Singular, dual and plural
			 *    var editor = new $.fn.Editor( {
			 *      "ajax": "data/source",
			 *      "table": "#example",
			 *      "i18n": {
			 *        "remove": {
			 *          "confirm": {
			 *            "_": "Confirm deletion of %d records.",
			 *            "1": "Confirm deletion of record.",
			 *            "2": "Confirm deletion of both record."
			 *        }
			 *      }
			 *    } );
			 *        
			 */
			"confirm": {
				"_": "Are you sure you wish to delete %d rows?",
				"1": "Are you sure you wish to delete 1 row?"
			}
		},

		/**
		 * Strings used for error conditions.
		 *  @namespace
		 */
		"error": {
			/**
			 * Generic server error message
			 *  @type string
			 *  @default A system error has occurred (<a target=\"_blank\" href=\"//datatables.net/tn/12\">More information</a>)
			 */
			"system": "A system error has occurred (<a target=\"_blank\" href=\"//datatables.net/tn/12\">More information</a>)."
		},

		/**
		 * Strings used for multi-value editing
		 *  @namespace
		 */
		multi: {
			/**
			 * Shown in place of the field value when a field has multiple values
			 */
			title: "Multiple values",

			/**
			 * Shown below the multi title text, although only the first
			 * instance of this text is shown in the form to reduce redundancy
			 */
			info: "The selected items contain different values for this input. To edit and set all items for this input to the same value, click or tap here, otherwise they will retain their individual values.",

			/**
			 * Shown below the field input when group editing a value to allow
			 * the user to return to the original multiple values
			 */
			restore: "Undo changes",


			/**
			 * Disabled for multi-row editing
			 */
			noMulti: "This input can be edited individually, but not part of a group."
		},

		"datetime": {
			previous: 'Previous',
			next:     'Next',
			months:   [ 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December' ],
			weekdays: [ 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat' ],
			amPm:     [ 'am', 'pm' ],
			unknown:  '-'
		}
	},

	formOptions: {
		bubble: $.extend( {}, Editor.models.formOptions, {
			title: false,
			message: false,
			buttons: '_basic',
			submit: 'changed'
		} ),

		inline: $.extend( {}, Editor.models.formOptions, {
			buttons: false,
			submit: 'changed'
		} ),

		main: $.extend( {}, Editor.models.formOptions )
	},

	/**
	 * Submit data to the server in the 1.4- data format (`true`) or in the 1.5+
	 * data format (`false` - default).
	 *
	 * @type Boolean
	 */
	legacyAjax: false
};


/*
 * Extensions
 */

(function(){


var __dataSources = Editor.dataSources = {};


/* -  -  -  -  -  -  -  -  -  -
 * DataTables editor interface
 */

var __dtIsSsp = function ( dt, editor ) {
	// If the draw type is `none`, then we still need to use the DT API to
	// update the display with the new data
	return dt.settings()[0].oFeatures.bServerSide &&
		editor.s.editOpts.drawType !== 'none';
};

var __dtApi = function ( table ) {
	return $(table).DataTable();
};

var __dtHighlight = function ( node ) {
	// Highlight a row using CSS transitions. The timeouts need to match the
	// transition duration from the CSS
	node = $(node);

	setTimeout( function () {
		node.addClass( 'highlight' );

		setTimeout( function () {
			node
				.addClass( 'noHighlight' )
				.removeClass( 'highlight' );

			setTimeout( function () {
				node.removeClass( 'noHighlight' );
			}, 550 );
		}, 500 );
	}, 20 );
};

var __dtRowSelector = function ( out, dt, identifier, fields, idFn )
{
	dt.rows( identifier ).indexes().each( function ( idx ) {
		var row = dt.row( idx );
		var data = row.data();
		var idSrc = idFn( data );

		if ( idSrc === undefined ) {
			Editor.error( 'Unable to find row identifier', 14 );
		}

		out[ idSrc ] = {
			idSrc:  idSrc,
			data:   data,
			node:   row.node(),
			fields: fields,
			type:   'row'
		};
	} );
};

var __dtFieldsFromIdx = function ( dt, fields, idx )
{
	var field;
	var col = dt.settings()[0].aoColumns[ idx ];
	var dataSrc = col.editField !== undefined ?
		col.editField :
		col.mData;
	var resolvedFields = {};
	var run = function ( field, dataSrc ) {
		if ( field.name() === dataSrc ) {
			resolvedFields[ field.name() ] = field;
		}
	};

	$.each( fields, function ( name, fieldInst ) {
		if ( $.isArray( dataSrc ) ) {
			for ( var i=0 ; i<dataSrc.length ; i++ ) {
				run( fieldInst, dataSrc[i] );
			}
		}
		else {
			run( fieldInst, dataSrc );
		}
	} );

	if ( $.isEmptyObject( resolvedFields ) ) {
		Editor.error('Unable to automatically determine field from source. Please specify the field name.', 11);
	}

	return resolvedFields;
};

var __dtCellSelector = function ( out, dt, identifier, allFields, idFn, forceFields )
{
	dt.cells( identifier ).indexes().each( function ( idx ) {
		var cell = dt.cell( idx );
		var row = dt.row( idx.row );
		var data = row.data();
		var idSrc = idFn( data );
		var fields = forceFields || __dtFieldsFromIdx( dt, allFields, idx.column );
		var isNode = (typeof identifier === 'object' && identifier.nodeName) || identifier instanceof $;
		var prevDisplayFields, prevAttach;

		// The row selector will create a new `out` object for the identifier, and the
		// cell selector might be called multiple times for a row, so we need to save
		// our specific items
		if ( out[ idSrc ] ) {
			prevAttach = out[ idSrc ].attach;
			prevDisplayFields = out[ idSrc ].displayFields;
		}

		// Use the row selector to get the row information
		__dtRowSelector(out, dt, idx.row, allFields, idFn);

		// Need to check if `attach / displayFields is present before writing
		out[ idSrc ].attach = prevAttach || [];
		out[ idSrc ].attach.push( isNode ?
			$(identifier).get(0) :
			cell.node()
		);

		out[ idSrc ].displayFields = prevDisplayFields || {};
		$.extend( out[ idSrc ].displayFields, fields );
	} );
};

var __dtColumnSelector = function ( out, dt, identifier, fields, idFn )
{
	dt.cells( null, identifier ).indexes().each( function ( idx ) {
		__dtCellSelector( out, dt, idx, fields, idFn );
	} );
};

var __dtjqId = function ( id ) {
	return typeof id === 'string' ?
		'#'+id.replace( /(:|\.|\[|\]|,)/g, '\\$1' ) :
		'#'+id;
};



__dataSources.dataTable = {
	individual: function ( identifier, fieldNames ) {
		var idFn = DataTable.ext.oApi._fnGetObjectDataFn( this.s.idSrc );
		var dt = __dtApi( this.s.table );
		var fields = this.s.fields;
		var out = {};
		var forceFields;
		var responsiveNode;

		if ( fieldNames ) {
			if ( ! $.isArray( fieldNames ) ) {
				fieldNames = [ fieldNames ];
			}

			forceFields = {};

			$.each( fieldNames, function ( i, name ) {
				forceFields[ name ] = fields[ name ];
			} );
		}

		__dtCellSelector( out, dt, identifier, fields, idFn, forceFields );

		return out;
	},

	// get idSrc, fields to edit, data and node for each item
	fields: function ( identifier )
	{
		var idFn = DataTable.ext.oApi._fnGetObjectDataFn( this.s.idSrc );
		var dt = __dtApi( this.s.table );
		var fields = this.s.fields;
		var out = {};

		if ( $.isPlainObject( identifier ) && ( identifier.rows !== undefined || identifier.columns !== undefined || identifier.cells !== undefined ) ) {
			// Multi-item type selector
			if ( identifier.rows !== undefined ) {
				__dtRowSelector( out, dt, identifier.rows, fields, idFn );
			}

			if ( identifier.columns !== undefined ) {
				__dtColumnSelector( out, dt, identifier.columns, fields, idFn );
			}
			
			if ( identifier.cells !== undefined ) {
				__dtCellSelector( out, dt, identifier.cells, fields, idFn );
			}
		}
		else {
			// Just a rows selector
			__dtRowSelector( out, dt, identifier, fields, idFn );
		}

		return out;
	},

	create: function ( fields, data ) {
		var dt = __dtApi( this.s.table );

		if ( ! __dtIsSsp( dt, this ) ) {
			var row = dt.row.add( data );
			__dtHighlight( row.node() );
		}
	},

	edit: function ( identifier, fields, data, store ) {
		var dt = __dtApi( this.s.table );

		// No point in doing anything when server-side processing - the commit
		// will redraw the table
		if ( ! __dtIsSsp( dt, this ) || this.s.editOpts.drawType === 'none' ) {
			// The identifier can select one or more rows, but the data will
			// refer to just a single row. We need to determine which row from
			// the set is the one to operator on.
			var idFn = DataTable.ext.oApi._fnGetObjectDataFn( this.s.idSrc );
			var rowId = idFn( data );
			var row;

			// Find the row to edit - attempt to do an id look up first for speed
			try {
				row = dt.row( __dtjqId(rowId) );
			}
			catch (e) {
				row = dt;
			}

			// If not found, then we need to do it the slow way
			if ( ! row.any() ) {
				row = dt.row( function ( rowIdx, rowData, rowNode ) {
					return rowId == idFn( rowData );
				} );
			}

			if ( row.any() ) {
				row.data( data );

				// Remove the item from the list of indexes now that is has been
				// updated
				var idx = $.inArray( rowId, store.rowIds );
				store.rowIds.splice( idx, 1 );
			}
			else {
				// If not found, then its a new row (change in pkey possibly)
				row = dt.row.add( data );
			}

			__dtHighlight( row.node() );
		}
	},

	remove: function ( identifier, fields, store ) {
		// No confirmation from the server 
		var dt = __dtApi( this.s.table );
		var cancelled = store.cancelled;

		if ( cancelled.length === 0 ) {
			// No rows were cancelled on the server-side, remove them all
			dt.rows( identifier ).remove();
		}
		else {
			// One or more rows were cancelled, so we need to identify them
			// and not remove those rows
			var idFn = DataTable.ext.oApi._fnGetObjectDataFn( this.s.idSrc );
			var indexes = [];

			dt.rows( identifier ).every( function () {
				var id = idFn( this.data() );

				if ( $.inArray( id, cancelled ) === -1 ) {
					// Don't use `remove` here - it messes up the indexes
					indexes.push( this.index() );
				}
			} );

			dt.rows( indexes ).remove();
		}
	},

	prep: function ( action, identifier, submit, json, store ) {
		// On edit we store the ids of the rows that are being edited
		if ( action === 'edit' ) {
			var cancelled = json.cancelled || [];

			store.rowIds = $.map( submit.data, function ( val, key ) {
				return ! $.isEmptyObject( submit.data[ key ] ) && // was submitted
					$.inArray( key, cancelled ) === -1 ? // was not cancelled on the server-side
						key :
						undefined;
			} );
		}
		else if ( action === 'remove' ) {
			store.cancelled = json.cancelled || [];
		}
	},

	commit: function ( action, identifier, data, store ) {
		// Updates complete - redraw
		var dt = __dtApi( this.s.table );

		// On edit, if there are any rows left in the `store.rowIds`, then they
		// were not returned by the server and should be removed (they might not
		// meet filtering requirements any more for example)
		if ( action === 'edit' && store.rowIds.length ) {
			var ids = store.rowIds;
			var idFn = DataTable.ext.oApi._fnGetObjectDataFn( this.s.idSrc );
			var row;
			var compare = function ( id ) {
				return function ( rowIdx, rowData, rowNode ) {
					return id == idFn( rowData );
				};
			};

			for ( var i=0, ien=ids.length ; i<ien ; i++ ) {
				// Find the row to edit - attempt to do an id look up first for speed
				try {
					row = dt.row( __dtjqId(ids[i]) );
				}
				catch (e) {
					row = dt;
				}

				// If not found, then we need to do it the slow way
				if ( ! row.any() ) {
					row = dt.row( compare( ids[i] ) );
				}

				if ( row.any() ) {
					row.remove();
				}
			}
		}

		var drawType = this.s.editOpts.drawType;
		if ( drawType !== 'none' ) {
			dt.draw( drawType );
		}
	}
};



/* -  -  -  -  -  -  -  -
 * HTML editor interface
 */

function __html_el ( identifier, name ) {
	var context = document;

	if ( identifier !== 'keyless' ) {
		context = $('[data-editor-id="'+identifier+'"]');

		if ( context.length === 0 ) {
			throw 'Could not find an element with `data-editor-id` of: '+identifier;
		}
	}

	return $('[data-editor-field="'+name+'"]', context);
}

function __html_els ( identifier, names ) {
	var out = $();

	for ( var i=0, ien=names.length ; i<ien ; i++ ) {
		out = out.add( __html_el( identifier, names[i] ) );
	}

	return out;
}

function __html_get( identifier, dataSrc ) {
	var el = __html_el( identifier, dataSrc );

	return el.filter('[data-editor-value]').length ?
		el.attr( 'data-editor-value' ) :
		el.html();
}

function __html_set( identifier, fields, data ) {
	$.each( fields, function ( name, field ) {
		var val = field.valFromData( data );

		if ( val !== undefined ) {
			var el = __html_el( identifier, field.dataSrc() );

			if ( el.filter('[data-editor-value]').length ) {
				el.attr( 'data-editor-value', val );
			}
			else {
				el.each( function () {
					// This is very frustrating, but in IE if you just write directly
					// to innerHTML, and elements that are overwritten are GC'ed,
					// even if there is a reference to them elsewhere
					while ( this.childNodes.length ) {
						this.removeChild( this.firstChild );
					}
				} )
				.html( val );
			}
		}
	} );
}



__dataSources.html = {
	initField: function ( cfg ) {
		// This is before the field has been initialised so can't use it API
		var label = $('[data-editor-label="'+(cfg.data || cfg.name)+'"]');
		if ( ! cfg.label && label.length ) {
			cfg.label = label.html();
		}
	},

	individual: function ( identifier, fieldNames ) {
		var attachEl;

		// Auto detection of the field name and id
		if ( identifier instanceof $ || identifier.nodeName ) {
			attachEl = identifier;

			if ( ! fieldNames ) {
				fieldNames = [ $( identifier ).attr('data-editor-field') ];
			}

			var back = $.fn.addBack ? 'addBack' : 'andSelf';
			identifier = $( identifier ).parents('[data-editor-id]')[ back ]().data('editor-id');
		}

		// no id given and none found
		if ( ! identifier ) {
			identifier = 'keyless';
		}

		// no field name - cannot continue
		if ( fieldNames && ! $.isArray( fieldNames ) ) {
			fieldNames = [ fieldNames ];
		}

		if ( ! fieldNames || fieldNames.length === 0 ) {
			throw 'Cannot automatically determine field name from data source';
		}

		var out = __dataSources.html.fields.call( this, identifier );
		var fields = this.s.fields;
		var forceFields = {};

		$.each( fieldNames, function ( i, name ) {
			forceFields[ name ] = fields[ name ];
		} );

		$.each( out, function ( id, set ) {
			set.type = 'cell';
			set.attach = attachEl ?
				$(attachEl) :
				__html_els( identifier, fieldNames ).toArray();
			set.fields = fields;
			set.displayFields = forceFields;
		} );

		return out;
	},

	// get idSrc, fields to edit, data and node for each item
	fields: function ( identifier )
	{
		var out = {};
		var self = __dataSources.html;

		// Allow multi-point editing
		if ( $.isArray( identifier ) ) {
			for ( var i=0, ien=identifier.length ; i<ien ; i++ ) {
				var res = self.fields.call( this, identifier[i] );
				out[ identifier[i] ] = res[ identifier[i] ];
			}

			return out;
		}
		// else

		var data = {};
		var fields = this.s.fields;

		if ( ! identifier ) {
			identifier = 'keyless';
		}

		$.each( fields, function ( name, field ) {
			var val = __html_get( identifier, field.dataSrc() );

			// If no HTML element is present, jQuery returns null. We want undefined
			field.valToData( data, val === null ? undefined : val );
		} );

		out[ identifier ] = {
			idSrc: identifier,
			data: data,
			node: document,
			fields: fields,
			type: 'row'
		};

		return out;
	},

	create: function ( fields, data ) {
		// If there is an element with the id that has been created, then use it
		// to assign the values
		if ( data ) {
			var idFn = DataTable.ext.oApi._fnGetObjectDataFn( this.s.idSrc );
			var id = idFn( data );

			if ( $('[data-editor-id="'+id+'"]').length ) {
				__html_set( id, fields, data );
			}
		}
	},

	edit: function ( identifier, fields, data ) {
		// Get the ids from the returned data or `keyless` if not found
		var idFn = DataTable.ext.oApi._fnGetObjectDataFn( this.s.idSrc );
		var id = idFn( data ) || 'keyless';

		__html_set( id, fields, data );
	},

	remove: function ( identifier, fields ) {
		// If there is an element with an ID property matching the identifier,
		// remove it
		$('[data-editor-id="'+identifier+'"]').remove();
	}
};


}());



/**
 * Class names that are used by Editor for its various display components.
 * A copy of this object is taken when an Editor instance is initialised, thus
 * allowing different classes to be used in different instances if required.
 * Class name changes can be useful for easy integration with CSS frameworks,
 * for example Twitter Bootstrap.
 *  @namespace
 */
Editor.classes = {
	/**
	 * Applied to the base DIV element that contains all other Editor elements
	 */
	"wrapper": "DTE",

	/**
	 * Processing classes
	 *  @namespace
	 */
	"processing": {
		/**
		 * Processing indicator element
		 */
		"indicator": "DTE_Processing_Indicator",

		/**
		 * Added to the base element ("wrapper") when the form is "processing"
		 */
		"active": "processing"
	},

	/**
	 * Display header classes
	 *  @namespace
	 */
	"header": {
		/**
		 * Container for the header elements
		 */
		"wrapper": "DTE_Header",

		/**
		 * Liner for the header content
		 */
		"content": "DTE_Header_Content"
	},

	/**
	 * Display body classes
	 *  @namespace
	 */
	"body": {
		/**
		 * Container for the body elements
		 */
		"wrapper": "DTE_Body",

		/**
		 * Liner for the body content
		 */
		"content": "DTE_Body_Content"
	},

	/**
	 * Display footer classes
	 *  @namespace
	 */
	"footer": {
		/**
		 * Container for the footer elements
		 */
		"wrapper": "DTE_Footer",
		
		/**
		 * Liner for the footer content
		 */
		"content": "DTE_Footer_Content"
	},

	/**
	 * Form classes
	 *  @namespace
	 */
	"form": {
		/**
		 * Container for the form elements
		 */
		"wrapper": "DTE_Form",

		/**
		 * Liner for the form content
		 */
		"content": "DTE_Form_Content",

		/**
		 * Applied to the <form> tag
		 */
		"tag":     "",

		/**
		 * Global form information
		 */
		"info":    "DTE_Form_Info",

		/**
		 * Global error imformation
		 */
		"error":   "DTE_Form_Error",

		/**
		 * Buttons container
		 */
		"buttons": "DTE_Form_Buttons",

		/**
		 * Buttons container
		 */
		"button": "btn"
	},

	/**
	 * Field classes
	 *  @namespace
	 */
	"field": {
		/**
		 * Container for each field
		 */
		"wrapper":     "DTE_Field",

		/**
		 * Class prefix for the field type - field type is added to the end allowing
		 * styling based on field type.
		 */
		"typePrefix":  "DTE_Field_Type_",

		/**
		 * Class prefix for the field name - field name is added to the end allowing
		 * styling based on field name.
		 */
		"namePrefix":  "DTE_Field_Name_",

		/**
		 * Field label
		 */
		"label":       "DTE_Label",

		/**
		 * Field input container
		 */
		"input":       "DTE_Field_Input",

		/**
		 * Input elements wrapper
		 */
		"inputControl": "DTE_Field_InputControl",

		/**
		 * Field error state (added to the field.wrapper element when in error state
		 */
		"error":       "DTE_Field_StateError",

		/**
		 * Label information text
		 */
		"msg-label":   "DTE_Label_Info",

		/**
		 * Error information text
		 */
		"msg-error":   "DTE_Field_Error",

		/**
		 * Live messaging (API) information text
		 */
		"msg-message": "DTE_Field_Message",

		/**
		 * General information text
		 */
		"msg-info":    "DTE_Field_Info",

		/**
		 * Multi-value information display wrapper
		 */
		"multiValue":  "multi-value",

		/**
		 * Multi-value information descriptive text
		 */
		"multiInfo":  "multi-info",

		/**
		 * Multi-value information display
		 */
		"multiRestore":  "multi-restore",

		/**
		 * Multi-value not editable (field.multiEditable)
		 */
		"multiNoEdit": "multi-noEdit",

		/**
		 * Field is disabled
		 */
		"disabled": "disabled"
	},

	/**
	 * Action classes - these are added to the Editor base element ("wrapper")
	 * and allows styling based on the type of form view that is being employed.
	 *  @namespace
	 */
	"actions": {
		/**
		 * Editor is in 'create' state
		 */
		"create": "DTE_Action_Create",

		/**
		 * Editor is in 'edit' state
		 */
		"edit":   "DTE_Action_Edit",

		/**
		 * Editor is in 'remove' state
		 */
		"remove": "DTE_Action_Remove"
	},

	/**
	 * Inline editing classes - these are used to display the inline editor
	 *  @namespace
	 */
	"inline": {
		"wrapper": "DTE DTE_Inline",

		"liner": "DTE_Inline_Field",

		"buttons": "DTE_Inline_Buttons"
	},

	/**
	 * Bubble editing classes - these are used to display the bubble editor
	 *  @namespace
	 */
	"bubble": {
		/**
		 * Bubble container element
		 */
		"wrapper": "DTE DTE_Bubble",

		/**
		 * Bubble content liner
		 */
		"liner": "DTE_Bubble_Liner",

		/**
		 * Bubble table display wrapper, so the buttons and form can be shown
		 * as table cells (via css)
		 */
		"table": "DTE_Bubble_Table",

		/**
		 * Close button
		 */
		"close": "icon close",

		/**
		 * Pointer shown which node is being edited
		 */
		"pointer": "DTE_Bubble_Triangle",

		/**
		 * Fixed background
		 */
		"bg": "DTE_Bubble_Background"
	}
};


/*
 * Add helpful buttons to make life easier
 *
 * Note that the values that require a string to make any sense (the button text
 * for example) are set by Editor when Editor is initialised through the i18n
 * options.
 */
(function () {

if ( DataTable.TableTools ) {
	var ttButtons = DataTable.TableTools.BUTTONS;
	var ttButtonBase = {
		sButtonText: null,
		editor:      null,
		formTitle:   null
	};

	ttButtons.editor_create = $.extend( true, ttButtons.text, ttButtonBase, {
		formButtons: [ {
			label: null,
			fn: function (e) { this.submit(); }
		} ],

		fnClick: function( button, config ) {
			var editor = config.editor;
			var i18nCreate = editor.i18n.create;
			var buttons = config.formButtons;

			if ( ! buttons[0].label ) {
				buttons[0].label = i18nCreate.submit;
			}

			editor.create( {
				title: i18nCreate.title,
				buttons: buttons
			} );
		}
	} );


	ttButtons.editor_edit = $.extend( true, ttButtons.select_single, ttButtonBase, {
		formButtons: [ {
			label: null,
			fn: function (e) { this.submit(); }
		} ],

		fnClick: function( button, config ) {
			var selected = this.fnGetSelectedIndexes();
			if ( selected.length !== 1 ) {
				return;
			}

			var editor = config.editor;
			var i18nEdit = editor.i18n.edit;
			var buttons = config.formButtons;

			if ( ! buttons[0].label ) {
				buttons[0].label = i18nEdit.submit;
			}

			editor.edit( selected[0], {
				title: i18nEdit.title,
				buttons: buttons
			} );
		}
	} );


	ttButtons.editor_remove = $.extend( true, ttButtons.select, ttButtonBase, {
		question: null,

		formButtons: [
			{
				label: null,
				fn: function (e) {
					// Executed in the Form instance's scope
					var that = this;
					this.submit( function ( json ) {
						var tt = $.fn.dataTable.TableTools.fnGetInstance(
							$(that.s.table).DataTable().table().node()
						);
						tt.fnSelectNone();
					} );
				}
			}
		],

		fnClick: function( button, config ) {
			var rows = this.fnGetSelectedIndexes();
			if ( rows.length === 0 ) {
				return;
			}

			var editor = config.editor;
			var i18nRemove = editor.i18n.remove;
			var buttons = config.formButtons;
			var question = typeof i18nRemove.confirm === 'string' ?
				i18nRemove.confirm :
				i18nRemove.confirm[rows.length] ?
					i18nRemove.confirm[rows.length] : i18nRemove.confirm._;

			if ( ! buttons[0].label ) {
				buttons[0].label = i18nRemove.submit;
			}

			editor.remove( rows, {
				message: question.replace( /%d/g, rows.length ),
				title: i18nRemove.title,
				buttons: buttons
			} );
		}
	} );
}

var _buttons = DataTable.ext.buttons;


$.extend( _buttons, {
	create: {
		text: function ( dt, node, config ) {
			return dt.i18n( 'buttons.create', config.editor.i18n.create.button );
		},
		className: 'buttons-create',
		editor: null,
		formButtons: {
			text: function ( editor ) {
				return editor.i18n.create.submit;
			},
			action: function (e) {
				this.submit();
			}
		},
		formMessage: null,
		formTitle: null,
		action: function( e, dt, node, config ) {
			var editor = config.editor;
			var buttons = config.formButtons;

			editor.create( {
				buttons: config.formButtons,
				message: config.formMessage,
				title:   config.formTitle || editor.i18n.create.title
			} );
		}
	},

	edit: {
		extend: 'selected',
		text: function ( dt, node, config ) {
			return dt.i18n( 'buttons.edit', config.editor.i18n.edit.button );
		},
		className: 'buttons-edit',
		editor: null,
		formButtons: {
			text: function ( editor ) {
				return editor.i18n.edit.submit;
			},
			action: function (e) {
				this.submit();
			}
		},
		formMessage: null,
		formTitle: null,
		action: function( e, dt, node, config ) {
			var editor = config.editor;
			var rows = dt.rows( { selected: true } ).indexes();
			var columns = dt.columns( { selected: true } ).indexes();
			var cells = dt.cells( { selected: true } ).indexes();

			var items = columns.length || cells.length ?
				{
					rows: rows,
					columns: columns,
					cells: cells
				} :
				rows;

			editor.edit( items, {
				message: config.formMessage,
				buttons: config.formButtons,
				title:   config.formTitle || editor.i18n.edit.title
			} );
		}
	},

	remove: {
		extend: 'selected',
		limitTo: ['rows'],
		text: function ( dt, node, config ) {
			return dt.i18n( 'buttons.remove', config.editor.i18n.remove.button );
		},
		className: 'buttons-remove',
		editor: null,
		formButtons: {
			text: function ( editor ) {
				return editor.i18n.remove.submit;
			},
			action: function (e) {
				this.submit();
			}
		},
		formMessage: function ( editor, dt ) {
			var rows = dt.rows( { selected: true } ).indexes();
			var i18n = editor.i18n.remove;
			var question = typeof i18n.confirm === 'string' ?
				i18n.confirm :
				i18n.confirm[rows.length] ?
					i18n.confirm[rows.length] : i18n.confirm._;

			return question.replace( /%d/g, rows.length );
		},
		formTitle: null,
		action: function( e, dt, node, config ) {
			var editor = config.editor;

			editor.remove( dt.rows( { selected: true } ).indexes(), {
				buttons: config.formButtons,
				message: config.formMessage,
				title:   config.formTitle || editor.i18n.remove.title
			} );
		}
	}
} );

// Reuse the standard edit and remove buttons for their singular equivalent,
// but set it to extend the single selected button only
_buttons.editSingle = $.extend( {}, _buttons.edit );
_buttons.editSingle.extend = 'selectedSingle';

_buttons.removeSingle = $.extend( {}, _buttons.remove );
_buttons.removeSingle.extend = 'selectedSingle';

}());

/**
 * Field types array - this can be used to add field types or modify the pre-
 * defined options. See the online Editor documentation for information about
 * the built in field types.
 *
 * Note that we use a DataTables ext object to allow plug-ins to be loaded
 * before Editor itself. This is useful for the online DataTables download
 * builder.
 *
 *  @namespace
 */
Editor.fieldTypes = {};
/*
 * This file provides a DateTime GUI picker (calendar and time input). Only the
 * format YYYY-MM-DD is supported without additional software, but the end user
 * experience can be greatly enhanced by including the momentjs library which
 * provides date / time parsing and formatting options.
 *
 * This functionality is required because the HTML5 date and datetime input
 * types are not widely supported in desktop browsers.
 *
 * Constructed by using:
 *
 *     new Editor.DateTime( input, opts )
 *
 * where `input` is the HTML input element to use and `opts` is an object of
 * options based on the `Editor.DateTime.defaults` object.
 */

Editor.DateTime = function ( input, opts ) {
	this.c = $.extend( true, {}, Editor.DateTime.defaults, opts );
	var classPrefix = this.c.classPrefix;
	var i18n = this.c.i18n;

	// Only IS8601 dates are supported without moment
	if ( ! window.moment && this.c.format !== 'YYYY-MM-DD' ) {
		throw "Editor datetime: Without momentjs only the format 'YYYY-MM-DD' can be used";
	}

	var timeBlock = function ( type ) {
		return '<div class="'+classPrefix+'-timeblock">'+
				'<div class="'+classPrefix+'-iconUp">'+
					'<button>'+i18n.previous+'</button>'+
				'</div>'+
				'<div class="'+classPrefix+'-label">'+
					'<span/>'+
					'<select class="'+classPrefix+'-'+type+'"/>'+
				'</div>'+
				'<div class="'+classPrefix+'-iconDown">'+
					'<button>'+i18n.next+'</button>'+
				'</div>'+
			'</div>';
	};

	var gap = function () {
		return '<span>:</span>';
	};

	// DOM structure
	var structure = $(
		'<div class="'+classPrefix+'">'+
			'<div class="'+classPrefix+'-date">'+
				'<div class="'+classPrefix+'-title">'+
					'<div class="'+classPrefix+'-iconLeft">'+
						'<button>'+i18n.previous+'</button>'+
					'</div>'+
					'<div class="'+classPrefix+'-iconRight">'+
						'<button>'+i18n.next+'</button>'+
					'</div>'+
					'<div class="'+classPrefix+'-label">'+
						'<span/>'+
						'<select class="'+classPrefix+'-month"/>'+
					'</div>'+
					'<div class="'+classPrefix+'-label">'+
						'<span/>'+
						'<select class="'+classPrefix+'-year"/>'+
					'</div>'+
				'</div>'+
				'<div class="'+classPrefix+'-calendar"/>'+
			'</div>'+
			'<div class="'+classPrefix+'-time">'+
				timeBlock( 'hours' )+
				gap()+
				timeBlock( 'minutes' )+
				gap()+
				timeBlock( 'seconds' )+
				timeBlock( 'ampm' )+
			'</div>'+
			'<div class="'+classPrefix+'-error"/>'+
		'</div>'
	);

	this.dom = {
		container: structure,
		date:      structure.find( '.'+classPrefix+'-date' ),
		title:     structure.find( '.'+classPrefix+'-title' ),
		calendar:  structure.find( '.'+classPrefix+'-calendar' ),
		time:      structure.find( '.'+classPrefix+'-time' ),
		error:     structure.find( '.'+classPrefix+'-error' ),
		input:     $(input)
	};

	this.s = {
		/** @type {Date} Date value that the picker has currently selected */
		d: null,

		/** @type {Date} Date of the calendar - might not match the value */
		display: null,

		/** @type {String} Unique namespace string for this instance */
		namespace: 'editor-dateime-'+(Editor.DateTime._instance++),

		/** @type {Object} Parts of the picker that should be shown */
		parts: {
			date:    this.c.format.match( /[YMD]|L(?!T)|l/ ) !== null,
			time:    this.c.format.match( /[Hhm]|LT|LTS/ ) !== null,
			seconds: this.c.format.indexOf( 's' )   !== -1,
			hours12: this.c.format.match( /[haA]/ ) !== null
		}
	};

	this.dom.container
		.append( this.dom.date )
		.append( this.dom.time )
		.append( this.dom.error );

	this.dom.date
		.append( this.dom.title )
		.append( this.dom.calendar );

	this._constructor();
};

$.extend( Editor.DateTime.prototype, {
	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Public
	 */
	
	/**
	 * Destroy the control
	 */
	destroy: function () {
		this._hide();
		this.dom.container.off().empty();
		this.dom.input.off('.editor-datetime');
	},

	errorMsg: function ( msg ) {
		var error = this.dom.error;

		if ( msg ) {
			error.html( msg );
		}
		else {
			error.empty();
		}
	},

	hide: function () {
		this._hide();
	},

	max: function ( date ) {
		this.c.maxDate = date;

		this._optionsTitle();
		this._setCalander();
	},

	min: function ( date ) {
		this.c.minDate = date;

		this._optionsTitle();
		this._setCalander();
	},

	/**
	 * Check if an element belongs to this control
	 *
	 * @param  {node} node Element to check
	 * @return {boolean}   true if owned by this control, false otherwise
	 */
	owns: function ( node ) {
		return $(node).parents().filter( this.dom.container ).length > 0;
	},

	/**
	 * Get / set the value
	 *
	 * @param  {string|Date} set   Value to set
	 * @param  {boolean} [write=true] Flag to indicate if the formatted value
	 *   should be written into the input element
	 */
	val: function ( set, write ) {
		if ( set === undefined ) {
			return this.s.d;
		}

		if ( set instanceof Date ) {
			this.s.d = this._dateToUtc( set );
		}
		else if ( set === null || set === '' ) {
			this.s.d = null;
		}
		else if ( typeof set === 'string' ) {
			if ( window.moment ) {
				// Use moment if possible (even for ISO8601 strings, since it
				// will correctly handle 0000-00-00 and the like)
				var m = window.moment.utc( set, this.c.format, this.c.momentLocale, this.c.momentStrict );
				this.s.d = m.isValid() ? m.toDate() : null;
			}
			else {
				// Else must be using ISO8601 without moment (constructor would
				// have thrown an error otherwise)
				var match = set.match(/(\d{4})\-(\d{2})\-(\d{2})/ );
				this.s.d = match ?
					new Date( Date.UTC(match[1], match[2]-1, match[3]) ) :
					null;
			}
		}

		if ( write || write === undefined ) {
			if ( this.s.d ) {
				this._writeOutput();
			}
			else {
				// The input value was not valid...
				this.dom.input.val( set );
			}
		}

		// We need a date to be able to display the calendar at all
		if ( ! this.s.d ) {
			this.s.d = this._dateToUtc( new Date() );
		}

		this.s.display = new Date( this.s.d.toString() );

		// Set the day of the month to be 1 so changing between months doesn't
        // run into issues when going from day 31 to 28 (for example)
		this.s.display.setUTCDate( 1 );

		// Update the display elements for the new value
		this._setTitle();
		this._setCalander();
		this._setTime();
	},


	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Constructor
	 */
	
	/**
	 * Build the control and assign initial event handlers
	 *
	 * @private
	 */
	_constructor: function () {
		var that = this;
		var classPrefix = this.c.classPrefix;
		var container = this.dom.container;
		var i18n = this.c.i18n;
		var onChange = this.c.onChange;

		if ( ! this.s.parts.date ) {
			this.dom.date.css( 'display', 'none' );
		}

		if ( ! this.s.parts.time ) {
			this.dom.time.css( 'display', 'none' );
		}

		if ( ! this.s.parts.seconds ) {
			this.dom.time.children('div.editor-datetime-timeblock').eq(2).remove();
			this.dom.time.children('span').eq(1).remove();
		}

		if ( ! this.s.parts.hours12 ) {
			this.dom.time.children('div.editor-datetime-timeblock').last().remove();
		}

		// Render the options
		this._optionsTitle();
		this._optionsTime( 'hours', this.s.parts.hours12 ? 12 : 24, 1 );
		this._optionsTime( 'minutes', 60, this.c.minutesIncrement );
		this._optionsTime( 'seconds', 60, this.c.secondsIncrement );
		this._options( 'ampm', [ 'am', 'pm' ], i18n.amPm );

		// Trigger the display of the widget when clicking or focusing on the
		// input element
		this.dom.input
			.on('focus.editor-datetime click.editor-datetime', function () {
				// If already visible - don't do anything
				if ( that.dom.container.is(':visible') || that.dom.input.is(':disabled') ) {
					return;
				}

				// In case the value has changed by text
				that.val( that.dom.input.val(), false );

				that._show();
			} )
			.on('keyup.editor-datetime', function () {
				// Update the calendar's displayed value as the user types
				if ( that.dom.container.is(':visible') ) {
					that.val( that.dom.input.val(), false );
				}
			} );

		// Main event handlers for input in the widget
		this.dom.container
			.on( 'change', 'select', function () {
				var select = $(this);
				var val = select.val();

				if ( select.hasClass(classPrefix+'-month') ) {
					// Month select
					that._correctMonth( that.s.display, val );
					that._setTitle();
					that._setCalander();
				}
				else if ( select.hasClass(classPrefix+'-year') ) {
					// Year select
					that.s.display.setUTCFullYear( val );
					that._setTitle();
					that._setCalander();
				}
				else if ( select.hasClass(classPrefix+'-hours') || select.hasClass(classPrefix+'-ampm') ) {
					// Hours - need to take account of AM/PM input if present
					if ( that.s.parts.hours12 ) {
						var hours = $(that.dom.container).find('.'+classPrefix+'-hours').val() * 1;
						var pm = $(that.dom.container).find('.'+classPrefix+'-ampm').val() === 'pm';

						that.s.d.setUTCHours( hours === 12 && !pm ?
							0 :
							pm && hours !== 12 ?
								hours + 12 :
								hours
						);
					}
					else {
						that.s.d.setUTCHours( val );
					}

					that._setTime();
					that._writeOutput( true );

					onChange();
				}
				else if ( select.hasClass(classPrefix+'-minutes') ) {
					// Minutes select
					that.s.d.setUTCMinutes( val );
					that._setTime();
					that._writeOutput( true );

					onChange();
				}
				else if ( select.hasClass(classPrefix+'-seconds') ) {
					// Seconds select
					that.s.d.setSeconds( val );
					that._setTime();
					that._writeOutput( true );

					onChange();
				}

				that.dom.input.focus();
				that._position();
			} )
			.on( 'click', function (e) {
				var nodeName = e.target.nodeName.toLowerCase();

				if ( nodeName === 'select' ) {
					return;
				}

				e.stopPropagation();

				if ( nodeName === 'button' ) {
					var button = $(e.target);
					var parent = button.parent();
					var select;

					if ( parent.hasClass('disabled') ) {
						return;
					}

					if ( parent.hasClass(classPrefix+'-iconLeft') ) {
						// Previous month
						that.s.display.setUTCMonth( that.s.display.getUTCMonth()-1 );
						that._setTitle();
						that._setCalander();

						that.dom.input.focus();
					}
					else if ( parent.hasClass(classPrefix+'-iconRight') ) {
						// Next month
						that._correctMonth( that.s.display, that.s.display.getUTCMonth()+1 );
						that._setTitle();
						that._setCalander();

						that.dom.input.focus();
					}
					else if ( parent.hasClass(classPrefix+'-iconUp') ) {
						// Value increase - common to all time selects
						select = parent.parent().find('select')[0];
						select.selectedIndex = select.selectedIndex !== select.options.length - 1 ?
							select.selectedIndex+1 :
							0;
						$(select).change();
					}
					else if ( parent.hasClass(classPrefix+'-iconDown') ) {
						// Value decrease - common to all time selects
						select = parent.parent().find('select')[0];
						select.selectedIndex = select.selectedIndex === 0 ?
							select.options.length - 1 :
							select.selectedIndex-1;
						$(select).change();
					}
					else {
						// Calendar click
						if ( ! that.s.d ) {
							that.s.d = that._dateToUtc( new Date() );
						}

						// Can't be certain that the current day will exist in
						// the new month, and likewise don't know that the
						// new day will exist in the old month, But 1 always
						// does, so we can change the month without worry of a
						// recalculation being done automatically by `Date`
						that.s.d.setUTCDate( 1 );
						that.s.d.setUTCFullYear( button.data('year') );
						that.s.d.setUTCMonth( button.data('month') );
						that.s.d.setUTCDate( button.data('day') );

						that._writeOutput( true );

						// Don't hide if there is a time picker, since we want to
						// be able to select a time as well.
						if ( ! that.s.parts.time ) {
							// This is annoying but IE has some kind of async
							// behaviour with focus and the focus from the above
							// write would occur after this hide - resulting in the
							// calendar opening immediately
							setTimeout( function () {
								that._hide();
							}, 10 );
						}
						else {
							that._setCalander();
						}

						onChange();
					}
				}
				else {
					// Click anywhere else in the widget - return focus to the
					// input element
					that.dom.input.focus();
				}
			} );
	},


	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Private
	 */

	/**
	 * Compare the date part only of two dates - this is made super easy by the
	 * toDateString method!
	 *
	 * @param  {Date} a Date 1
	 * @param  {Date} b Date 2
	 * @private
	 */
	_compareDates: function( a, b ) {
		// Can't use toDateString as that converts to local time
		return this._dateToUtcString(a) === this._dateToUtcString(b);
	},

	/**
	 * When changing month, take account of the fact that some months don't have
	 * the same number of days. For example going from January to February you
	 * can have the 31st of Jan selected and just add a month since the date
	 * would still be 31, and thus drop you into March.
	 *
	 * @param  {Date} date  Date - will be modified
	 * @param  {integer} month Month to set
	 * @private
	 */
	_correctMonth: function ( date, month ) {
		var days = this._daysInMonth( date.getUTCFullYear(), month );
		var correctDays = date.getUTCDate() > days;

		date.setUTCMonth( month );

		if ( correctDays ) {
			date.setUTCDate( days );
			date.setUTCMonth( month );
		}
	},

	/**
	 * Get the number of days in a method. Based on
	 * http://stackoverflow.com/a/4881951 by Matti Virkkunen
	 *
	 * @param  {integer} year  Year
	 * @param  {integer} month Month (starting at 0)
	 * @private
	 */
	_daysInMonth: function ( year, month ) {
		// 
		var isLeap = ((year % 4) === 0 && ((year % 100) !== 0 || (year % 400) === 0));
		var months = [31, (isLeap ? 29 : 28), 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

		return months[month];
	},

	/**
	 * Create a new date object which has the UTC values set to the local time.
	 * This allows the local time to be used directly for the library which
	 * always bases its calculations and display on UTC.
	 *
	 * @param  {Date} s Date to "convert"
	 * @return {Date}   Shifted date
	 */
	_dateToUtc: function ( s ) {
		return new Date( Date.UTC(
			s.getFullYear(), s.getMonth(), s.getDate(),
			s.getHours(), s.getMinutes(), s.getSeconds()
		) );
	},

	/**
	 * Create a UTC ISO8601 date part from a date object
	 *
	 * @param  {Date} d Date to "convert"
	 * @return {string} ISO formatted date
	 */
	_dateToUtcString: function ( d ) {
		return d.getUTCFullYear()+'-'+
			this._pad(d.getUTCMonth()+1)+'-'+
			this._pad(d.getUTCDate());
	},

	/**
	 * Hide the control and remove events related to its display
	 *
	 * @private
	 */
	_hide: function () {
		var namespace = this.s.namespace;

		this.dom.container.detach();

		$(window).off( '.'+namespace );
		$(document).off( 'keydown.'+namespace );
		$('div.DTE_Body_Content').off( 'scroll.'+namespace );
		$('body').off( 'click.'+namespace );
	},

	/**
	 * Convert a 24 hour value to a 12 hour value
	 *
	 * @param  {integer} val 24 hour value
	 * @return {integer}     12 hour value
	 * @private
	 */
	_hours24To12: function ( val ) {
		return val === 0 ?
			12 :
			val > 12 ?
				val - 12 :
				val;
	},

	/**
	 * Generate the HTML for a single day in the calendar - this is basically
	 * and HTML cell with a button that has data attributes so we know what was
	 * clicked on (if it is clicked on) and a bunch of classes for styling.
	 *
	 * @param  {object} day Day object from the `_htmlMonth` method
	 * @return {string}     HTML cell
	 */
	_htmlDay: function( day )
	{
		if ( day.empty ) {
			return '<td class="empty"></td>';
		}

		var classes = [ 'day' ];
		var classPrefix = this.c.classPrefix;

		if ( day.disabled ) {
			classes.push( 'disabled' );
		}

		if ( day.today ) {
			classes.push( 'today' );
		}

		if ( day.selected ) {
			classes.push( 'selected' );
		}

		return '<td data-day="' + day.day + '" class="' + classes.join(' ') + '">' +
				'<button class="'+classPrefix+'-button '+classPrefix+'-day" type="button" ' +'data-year="' + day.year + '" data-month="' + day.month + '" data-day="' + day.day + '">' +
						day.day +
				'</button>' +
			'</td>';
	},


	/**
	 * Create the HTML for a month to be displayed in the calendar table.
	 * 
	 * Based upon the logic used in Pikaday - MIT licensed
	 * Copyright (c) 2014 David Bushell
	 * https://github.com/dbushell/Pikaday
	 *
	 * @param  {integer} year  Year
	 * @param  {integer} month Month (starting at 0)
	 * @return {string} Calendar month HTML
	 * @private
	 */
	_htmlMonth: function ( year, month ) {
		var now    = this._dateToUtc( new Date() ),
			days   = this._daysInMonth( year, month ),
			before = new Date( Date.UTC(year, month, 1) ).getUTCDay(),
			data   = [],
			row    = [];

		if ( this.c.firstDay > 0 ) {
			before -= this.c.firstDay;

			if (before < 0) {
				before += 7;
			}
		}

		var cells = days + before,
			after = cells;

		while ( after > 7 ) {
			after -= 7;
		}

		cells += 7 - after;

		var minDate = this.c.minDate;
		var maxDate = this.c.maxDate;

		if ( minDate ) {
			minDate.setUTCHours(0);
			minDate.setUTCMinutes(0);
			minDate.setSeconds(0);
		}

		if ( maxDate ) {
			maxDate.setUTCHours(23);
			maxDate.setUTCMinutes(59);
			maxDate.setSeconds(59);
		}

		for ( var i=0, r=0 ; i<cells ; i++ ) {
			var day      = new Date( Date.UTC(year, month, 1 + (i - before)) ),
				selected = this.s.d ? this._compareDates(day, this.s.d) : false,
				today    = this._compareDates(day, now),
				empty    = i < before || i >= (days + before),
				disabled = (minDate && day < minDate) ||
				           (maxDate && day > maxDate);

			var disableDays = this.c.disableDays;
			if ( $.isArray( disableDays ) && $.inArray( day.getUTCDay(), disableDays ) !== -1 ) {
				disabled = true;
			}
			else if ( typeof disableDays === 'function' && disableDays( day ) === true ) {
				disabled = true;
			}

			var dayConfig = {
				day:      1 + (i - before),
				month:    month,
				year:     year,
				selected: selected,
				today:    today,
				disabled: disabled,
				empty:    empty
			};

			row.push( this._htmlDay(dayConfig) );

			if ( ++r === 7 ) {
				if ( this.c.showWeekNumber ) {
					row.unshift( this._htmlWeekOfYear(i - before, month, year) );
				}

				data.push( '<tr>'+row.join('')+'</tr>' );
				row = [];
				r = 0;
			}
		}

		var classPrefix = this.c.classPrefix;
		var className = classPrefix+'-table';
		if ( this.c.showWeekNumber ) {
			className += ' weekNumber';
		}

		// Show / hide month icons based on min/max
		var underMin = minDate > new Date( Date.UTC(year, month-1, 1, 0, 0, 0 ) );
		var overMax = maxDate < new Date( Date.UTC(year, month+1, 1, 0, 0, 0 ) );

		this.dom.title.find('div.'+classPrefix+'-iconLeft')
			.css( 'display', underMin ? 'none' : 'block' );

		this.dom.title.find('div.'+classPrefix+'-iconRight')
			.css( 'display', overMax ? 'none' : 'block' );

		return '<table class="'+className+'">' +
				'<thead>'+
					this._htmlMonthHead() +
				'</thead>'+
				'<tbody>'+
					data.join('') +
				'</tbody>'+
			'</table>';
	},

	/**
	 * Create the calendar table's header (week days)
	 *
	 * @return {string} HTML cells for the row
	 * @private
	 */
	_htmlMonthHead: function () {
		var a = [];
		var firstDay = this.c.firstDay;
		var i18n = this.c.i18n;

		// Take account of the first day shift
		var dayName = function ( day ) {
			day += firstDay;

			while (day >= 7) {
				day -= 7;
			}

			return i18n.weekdays[day];
		};
		
		// Empty cell in the header
		if ( this.c.showWeekNumber ) {
			a.push( '<th></th>' );
		}

		for ( var i=0 ; i<7 ; i++ ) {
			a.push( '<th>'+dayName( i )+'</th>' );
		}

		return a.join('');
	},

	/**
	 * Create a cell that contains week of the year - ISO8601
	 *
	 * Based on https://stackoverflow.com/questions/6117814/ and
	 * http://techblog.procurios.nl/k/n618/news/view/33796/14863/
	 *
	 * @param  {integer} d Day of month
	 * @param  {integer} m Month of year (zero index)
	 * @param  {integer} y Year
	 * @return {string}   
	 * @private
	 */
	_htmlWeekOfYear: function ( d, m, y ) {
		var date = new Date( y, m, d, 0, 0, 0, 0 );

		// First week of the year always has 4th January in it
		date.setDate( date.getDate() + 4 - (date.getDay() || 7) );

		var oneJan = new Date( y, 0, 1 );
		var weekNum = Math.ceil( ( ( (date - oneJan) / 86400000) + 1)/7 );

		return '<td class="'+this.c.classPrefix+'-week">' + weekNum + '</td>';
	},

	/**
	 * Create option elements from a range in an array
	 *
	 * @param  {string} selector Class name unique to the select element to use
	 * @param  {array} values   Array of values
	 * @param  {array} [labels] Array of labels. If given must be the same
	 *   length as the values parameter.
	 * @private
	 */
	_options: function ( selector, values, labels ) {
		if ( ! labels ) {
			labels = values;
		}

		var select = this.dom.container.find('select.'+this.c.classPrefix+'-'+selector);
		select.empty();

		for ( var i=0, ien=values.length ; i<ien ; i++ ) {
			select.append( '<option value="'+values[i]+'">'+labels[i]+'</option>' );
		}
	},

	/**
	 * Set an option and update the option's span pair (since the select element
	 * has opacity 0 for styling)
	 *
	 * @param  {string} selector Class name unique to the select element to use
	 * @param  {*}      val      Value to set
	 * @private
	 */
	_optionSet: function ( selector, val ) {
		var select = this.dom.container.find('select.'+this.c.classPrefix+'-'+selector);
		var span = select.parent().children('span');

		select.val( val );

		var selected = select.find('option:selected');
		span.html( selected.length !== 0 ?
			selected.text() :
			this.c.i18n.unknown
		);
	},

	/**
	 * Create time option list. Can't just use `_options` for the time as the
	 * hours can be a little complex and we want to be able to control the
	 * increment option for the minutes and seconds.
	 *
	 * @param  {jQuery} select Select element to operate on
	 * @param  {integer} count  Value to loop to
	 * @param  {integer} inc    Increment value
	 * @private
	 */
	_optionsTime: function ( select, count, inc ) {
		var classPrefix = this.c.classPrefix;
		var sel = this.dom.container.find('select.'+classPrefix+'-'+select);
		var start=0, end=count;
		var allowed = this.c.hoursAvailable;
		var render = count === 12 ?
			function (i) { return i; } :
			this._pad;

		if ( count === 12 ) {
			start = 1;
			end = 13;
		}

		for ( var i=start ; i<end ; i+=inc ) {
			if ( ! allowed || $.inArray( i, allowed ) !== -1 ) {
				sel.append( '<option value="'+i+'">'+render(i)+'</option>' );
			}
		}
	},

	/**
	 * Create the options for the month and year
	 *
	 * @param  {integer} year  Year
	 * @param  {integer} month Month (starting at 0)
	 * @private
	 */
	_optionsTitle: function ( year, month ) {
		var classPrefix = this.c.classPrefix;
		var i18n = this.c.i18n;
		var min = this.c.minDate;
		var max = this.c.maxDate;
		var minYear = min ? min.getFullYear() : null;
		var maxYear = max ? max.getFullYear() : null;

		var i = minYear !== null ? minYear : new Date().getFullYear() - this.c.yearRange;
		var j = maxYear !== null ? maxYear : new Date().getFullYear() + this.c.yearRange;

		this._options( 'month', this._range( 0, 11 ), i18n.months );
		this._options( 'year', this._range( i, j ) );
	},

	/**
	 * Simple two digit pad
	 *
	 * @param  {integer} i      Value that might need padding
	 * @return {string|integer} Padded value
	 * @private
	 */
	_pad: function ( i ) {
		return i<10 ? '0'+i : i;
	},

	/**
	 * Position the calendar to look attached to the input element
	 * @private
	 */
	_position: function () {
		var offset = this.dom.input.offset();
		var container = this.dom.container;
		var inputHeight = this.dom.input.outerHeight();

		container
			.css( {
				top: offset.top + inputHeight,
				left: offset.left
			} )
			.appendTo( 'body' );

		var calHeight = container.outerHeight();
		var calWidth = container.outerWidth();
		var scrollTop = $(window).scrollTop();

		// Correct to the bottom
		if ( offset.top + inputHeight + calHeight - scrollTop > $(window).height() ) {
			var newTop = offset.top - calHeight;

			container.css( 'top', newTop < 0 ? 0 : newTop );
		}

		// Correct to the right
		if ( calWidth + offset.left > $(window).width() ) {
			var newLeft = $(window).width() - calWidth;

			container.css( 'left', newLeft < 0 ? 0 : newLeft );
		}
	},

	/**
	 * Create a simple array with a range of values
	 *
	 * @param  {integer} start Start value (inclusive)
	 * @param  {integer} end   End value (inclusive)
	 * @return {array}         Created array
	 * @private
	 */
	_range: function ( start, end ) {
		var a = [];

		for ( var i=start ; i<=end ; i++ ) {
			a.push( i );
		}

		return a;
	},

	/**
	 * Redraw the calendar based on the display date - this is a destructive
	 * operation
	 *
	 * @private
	 */
	_setCalander: function () {
		if ( this.s.display ) {
			this.dom.calendar
				.empty()
				.append( this._htmlMonth(
					this.s.display.getUTCFullYear(),
					this.s.display.getUTCMonth()
				) );
		}
	},

	/**
	 * Set the month and year for the calendar based on the current display date
	 *
	 * @private
	 */
	_setTitle: function () {
		this._optionSet( 'month', this.s.display.getUTCMonth() );
		this._optionSet( 'year', this.s.display.getUTCFullYear() );
	},

	/**
	 * Set the time based on the current value of the widget
	 *
	 * @private
	 */
	_setTime: function () {
		var d = this.s.d;
		var hours = d ? d.getUTCHours() : 0;

		if ( this.s.parts.hours12 ) {
			this._optionSet( 'hours', this._hours24To12( hours ) );
			this._optionSet( 'ampm', hours < 12 ? 'am' : 'pm' );
		}
		else {
			this._optionSet( 'hours', hours );
		}

		this._optionSet( 'minutes', d ? d.getUTCMinutes() : 0 );
		this._optionSet( 'seconds', d ? d.getSeconds() : 0 );
	},

	/**
	 * Show the widget and add events to the document required only while it
	 * is displayed
	 * 
	 * @private
	 */
	_show: function () {
		var that = this;
		var namespace = this.s.namespace;

		this._position();

		// Need to reposition on scroll
		$(window).on( 'scroll.'+namespace+' resize.'+namespace, function () {
			that._position();
		} );

		$('div.DTE_Body_Content').on( 'scroll.'+namespace, function () {
			that._position();
		} );

		// On tab focus will move to a different field (no keyboard navigation
		// in the date picker - this might need to be changed).
		// On esc the Editor might close. Even if it doesn't the date picker
		// should
		$(document).on( 'keydown.'+namespace, function (e) {
			if (
				e.keyCode === 9  || // tab
				e.keyCode === 27 || // esc
				e.keyCode === 13    // return
			) {
				that._hide();
			}
		} );

		// Hide if clicking outside of the widget - but in a different click
		// event from the one that was used to trigger the show (bubble and
		// inline)
		setTimeout( function () {
			$('body').on( 'click.'+namespace, function (e) {
				var parents = $(e.target).parents();

				if ( ! parents.filter( that.dom.container ).length && e.target !== that.dom.input[0] ) {
					that._hide();
				}
			} );
		}, 10 );
	},

	/**
	 * Write the formatted string to the input element this control is attached
	 * to
	 *
	 * @private
	 */
	_writeOutput: function ( focus ) {
		var date = this.s.d;

		// Use moment if possible - otherwise it must be ISO8601 (or the
		// constructor would have thrown an error)
		var out = window.moment ?
			window.moment.utc( date, undefined, this.c.momentLocale, this.c.momentStrict ).format( this.c.format ) :
			date.getUTCFullYear() +'-'+
	            this._pad(date.getUTCMonth() + 1) +'-'+
	            this._pad(date.getUTCDate());
		
		this.dom.input.val( out );

		if ( focus ) {
			this.dom.input.focus();
		}
	}
} );


/**
 * For generating unique namespaces
 *
 * @type {Number}
 * @private
 */
Editor.DateTime._instance = 0;

/**
 * Defaults for the date time picker
 *
 * @type {Object}
 */
Editor.DateTime.defaults = {
	// Not documented - could be an internal property
	classPrefix: 'editor-datetime',

	// function or array of ints
	disableDays: null,

	// first day of the week (0: Sunday, 1: Monday, etc)
	firstDay: 1,

	format: 'YYYY-MM-DD',

	hoursAvailable: null,

	// Not documented as i18n is done by the Editor.defaults.i18n obj
	i18n: Editor.defaults.i18n.datetime,

	maxDate: null,

	minDate: null,

	minutesIncrement: 1,

	momentStrict: true,

	momentLocale: 'en',

	onChange: function () {},

	secondsIncrement: 1,

	// show the ISO week number at the head of the row
	showWeekNumber: false,

	// overruled by max / min date
	yearRange: 10
};



(function() {

var fieldTypes = Editor.fieldTypes;

// Upload private helper method
function _buttonText ( conf, text )
{
	if ( text === null || text === undefined ) {
		text = conf.uploadText || "Choose file...";
	}

	conf._input.find('div.upload button').html( text );
}

function _commonUpload ( editor, conf, dropCallback )
{
	var btnClass = editor.classes.form.button;
	var container = $(
		'<div class="editor_upload">'+
			'<div class="eu_table">'+
				'<div class="row">'+
					'<div class="cell upload">'+
						'<button class="'+btnClass+'" />'+
						'<input type="file"/>'+
					'</div>'+
					'<div class="cell clearValue">'+
						'<button class="'+btnClass+'" />'+
					'</div>'+
				'</div>'+
				'<div class="row second">'+
					'<div class="cell">'+
						'<div class="drop"><span/></div>'+
					'</div>'+
					'<div class="cell">'+
						'<div class="rendered"/>'+
					'</div>'+
				'</div>'+
			'</div>'+
		'</div>'
	);

	conf._input = container;
	conf._enabled = true;

	_buttonText( conf );

	if ( window.FileReader && conf.dragDrop !== false ) {
		container.find('div.drop span').text(
			conf.dragDropText || "Drag and drop a file here to upload"
		);

		var dragDrop = container.find('div.drop');
		dragDrop
			.on( 'drop', function (e) {
				if ( conf._enabled ) {
					Editor.upload( editor, conf, e.originalEvent.dataTransfer.files, _buttonText, dropCallback );
					dragDrop.removeClass('over');
				}
				return false;
			} )
			.on( 'dragleave dragexit', function (e) {
				if ( conf._enabled ) {
					dragDrop.removeClass('over');
				}
				return false;
			} )
			.on( 'dragover', function (e) {
				if ( conf._enabled ) {
					dragDrop.addClass('over');
				}
				return false;
			} );

		// When an Editor is open with a file upload input there is a
		// reasonable chance that the user will miss the drop point when
		// dragging and dropping. Rather than loading the file in the browser,
		// we want nothing to happen, otherwise the form will be lost.
		editor
			.on( 'open', function () {
				$('body').on( 'dragover.DTE_Upload drop.DTE_Upload', function (e) {
					return false;
				} );
			} )
			.on( 'close', function () {
				$('body').off( 'dragover.DTE_Upload drop.DTE_Upload' );
			} );
	}
	else {
		container.addClass( 'noDrop' );
		container.append( container.find('div.rendered') );
	}

	container.find('div.clearValue button').on( 'click', function () {
		Editor.fieldTypes.upload.set.call( editor, conf, '' );
	} );

	container.find('input[type=file]').on('change', function () {
		Editor.upload( editor, conf, this.files, _buttonText, function (ids) {
			dropCallback.call( editor, ids );

			// Clear the value so change will happen on the next file select,
			// even if it is the same file
			container.find('input[type=file]').val('');
		} );
	} );

	return container;
}

// Typically a change event caused by the end user will be added to a queue that
// the browser will handle when no other script is running. However, using
// `$().trigger()` will cause it to happen immediately, so in order to simulate
// the standard browser behaviour we use setTimeout. This also means that
// `dependent()` and other change event listeners will trigger when the field
// values have all been set, rather than as they are being set - 31594
function _triggerChange ( input ) {
	setTimeout( function () {
		input.trigger( 'change', {editor: true, editorSet: true} ); // editorSet legacy
	}, 0 );
}


// A number of the fields in this file use the same get, set, enable and disable
// methods (specifically the text based controls), so in order to reduce the code
// size, we just define them once here in our own local base model for the field
// types.
var baseFieldType = $.extend( true, {}, Editor.models.fieldType, {
	get: function ( conf ) {
		return conf._input.val();
	},

	set: function ( conf, val ) {
		conf._input.val( val );
		_triggerChange( conf._input );
	},

	enable: function ( conf ) {
		conf._input.prop( 'disabled', false );
	},

	disable: function ( conf ) {
		conf._input.prop( 'disabled', true );
	},

	canReturnSubmit: function ( conf, node ) {
		return true;
	}
} );



fieldTypes.hidden = {
	create: function ( conf ) {
		conf._val = conf.value;
		return null;
	},

	get: function ( conf ) {
		return conf._val;
	},

	set: function ( conf, val ) {
		conf._val = val;
	}
};


fieldTypes.readonly = $.extend( true, {}, baseFieldType, {
	create: function ( conf ) {
		conf._input = $('<input/>').attr( $.extend( {
			id: Editor.safeId( conf.id ),
			type: 'text',
			readonly: 'readonly'
		}, conf.attr || {} ) );

		return conf._input[0];
	}
} );


fieldTypes.text = $.extend( true, {}, baseFieldType, {
	create: function ( conf ) {
		conf._input = $('<input/>').attr( $.extend( {
			id: Editor.safeId( conf.id ),
			type: 'text'
		}, conf.attr || {} ) );

		return conf._input[0];
	}
} );


fieldTypes.password = $.extend( true, {}, baseFieldType, {
	create: function ( conf ) {
		conf._input = $('<input/>').attr( $.extend( {
			id: Editor.safeId( conf.id ),
			type: 'password'
		}, conf.attr || {} ) );

		return conf._input[0];
	}
} );

fieldTypes.textarea = $.extend( true, {}, baseFieldType, {
	create: function ( conf ) {
		conf._input = $('<textarea/>').attr( $.extend( {
			id: Editor.safeId( conf.id )
		}, conf.attr || {} ) );
		return conf._input[0];
	},

	canReturnSubmit: function ( conf, node ) {
		return false;
	}
} );


fieldTypes.select = $.extend( true, {}, baseFieldType, {
	// Locally "private" function that can be reused for the create and update methods
	_addOptions: function ( conf, opts, append ) {
		var elOpts = conf._input[0].options;
		var countOffset = 0;

		if ( ! append ) {
			elOpts.length = 0;

			if ( conf.placeholder !== undefined ) {
				var placeholderValue = conf.placeholderValue !== undefined ?
					conf.placeholderValue :
					'';

				countOffset += 1;
				elOpts[0] = new Option( conf.placeholder, placeholderValue );

				var disabled = conf.placeholderDisabled !== undefined ?
					conf.placeholderDisabled :
					true;

				elOpts[0].hidden = disabled; // can't be hidden if not disabled!
				elOpts[0].disabled = disabled;
				elOpts[0]._editor_val = placeholderValue;
			}
		}
		else {
			countOffset = elOpts.length;
		}

		if ( opts ) {
			Editor.pairs( opts, conf.optionsPair, function ( val, label, i, attr ) {
				var option = new Option( label, val );
				option._editor_val = val;

				if ( attr ) {
					$(option).attr( attr );
				}

				elOpts[ i+countOffset ] = option;
			} );
		}
	},

	create: function ( conf ) {
		conf._input = $('<select/>')
			.attr( $.extend( {
				id: Editor.safeId( conf.id ),
				multiple: conf.multiple === true
			}, conf.attr || {} ) )
			.on( 'change.dte', function (e, d) {
				// On change, get the user selected value and store it as the
				// last set, so `update` can reflect it. This way `_lastSet`
				// always gives the intended value, be it set via the API or by
				// the end user.
				if ( ! d || ! d.editor ) {
					conf._lastSet = fieldTypes.select.get( conf );
				}
			} );

		fieldTypes.select._addOptions( conf, conf.options || conf.ipOpts );

		return conf._input[0];
	},

	update: function ( conf, options, append ) {
		fieldTypes.select._addOptions( conf, options, append );

		// Attempt to set the last selected value (set by the API or the end
		// user, they get equal priority)
		var lastSet = conf._lastSet;

		if ( lastSet !== undefined ) {
			fieldTypes.select.set( conf, lastSet, true );
		}

		_triggerChange( conf._input );
	},

	get: function ( conf ) {
		var val = conf._input.find('option:selected').map( function () {
			return this._editor_val;
		} ).toArray();

		if ( conf.multiple ) {
			return conf.separator ?
				val.join( conf.separator ) :
				val;
		}

		return val.length ? val[0] : null;
	},

	set: function ( conf, val, localUpdate ) {
		if ( ! localUpdate ) {
			conf._lastSet = val;
		}

		// Can't just use `$().val()` because it won't work with strong types
		if ( conf.multiple && conf.separator && ! $.isArray( val ) ) {
			val = typeof val === 'string' ?
				val.split( conf.separator ) :
				[];
		}
		else if ( ! $.isArray( val ) ) {
			val = [ val ];
		}

		var i, len=val.length, found, allFound = false;
		var options = conf._input.find('option');

		conf._input.find('option').each( function () {
			found = false;

			for ( i=0 ; i<len ; i++ ) {
				// Weak typing
				if ( this._editor_val == val[i] ) {
					found = true;
					allFound = true;
					break;
				}
			}

			this.selected = found;
		} );

		// If there is a placeholder, we might need to select it if nothing else
		// was selected. It doesn't make sense to select when multi is enabled
		if ( conf.placeholder && ! allFound && ! conf.multiple && options.length ) {
			options[0].selected = true;
		}

		// Update will call change itself, otherwise multiple might be called
		if ( ! localUpdate ) {
			_triggerChange( conf._input );
		}

		return allFound;
	},

	destroy: function ( conf ) {
		conf._input.off( 'change.dte' );
	}
} );


fieldTypes.checkbox = $.extend( true, {}, baseFieldType, {
	// Locally "private" function that can be reused for the create and update methods
	_addOptions: function ( conf, opts, append ) {
		var val, label;
		var jqInput = conf._input;
		var offset = 0;

		if ( ! append ) {
			jqInput.empty();
		}
		else {
			offset = $('input', jqInput).length;
		}

		if ( opts ) {
			Editor.pairs( opts, conf.optionsPair, function ( val, label, i, attr ) {
				jqInput.append(
					'<div>'+
						'<input id="'+Editor.safeId( conf.id )+'_'+(i+offset)+'" type="checkbox" />'+
						'<label for="'+Editor.safeId( conf.id )+'_'+(i+offset)+'">'+label+'</label>'+
					'</div>'
				);
				$('input:last', jqInput).attr('value', val)[0]._editor_val = val;

				if ( attr ) {
					$('input:last', jqInput).attr( attr );
				}
			} );
		}
	},


	create: function ( conf ) {
		conf._input = $('<div />');
		fieldTypes.checkbox._addOptions( conf, conf.options || conf.ipOpts );

		return conf._input[0];
	},

	get: function ( conf ) {
		var out = [];
		var selected = conf._input.find('input:checked');

		if ( selected.length ) {
			selected.each( function () {
				out.push( this._editor_val );
			} );
		}
		else if ( conf.unselectedValue !== undefined ) {
			out.push( conf.unselectedValue );
		}

		return conf.separator === undefined || conf.separator === null ?
			out :
			out.join(conf.separator);
	},

	set: function ( conf, val ) {
		var jqInputs = conf._input.find('input');
		if ( ! $.isArray(val) && typeof val === 'string' ) {
			val = val.split( conf.separator || '|' );
		}
		else if ( ! $.isArray(val) ) {
			val = [ val ];
		}

		var i, len=val.length, found;

		jqInputs.each( function () {
			found = false;

			for ( i=0 ; i<len ; i++ ) {
				if ( this._editor_val == val[i] ) {
					found = true;
					break;
				}
			}

			this.checked = found;
		} );

		_triggerChange( jqInputs );
	},

	enable: function ( conf ) {
		conf._input.find('input').prop('disabled', false);
	},

	disable: function ( conf ) {
		conf._input.find('input').prop('disabled', true);
	},

	update: function ( conf, options, append ) {
		// Get the current value
		var checkbox = fieldTypes.checkbox;
		var currVal = checkbox.get( conf );

		checkbox._addOptions( conf, options, append );
		checkbox.set( conf, currVal );
	}
} );


fieldTypes.radio = $.extend( true, {}, baseFieldType, {
	// Locally "private" function that can be reused for the create and update methods
	_addOptions: function ( conf, opts, append ) {
		var val, label;
		var jqInput = conf._input;
		var offset = 0;

		if ( ! append ) {
			jqInput.empty();
		}
		else {
			offset = $('input', jqInput).length;
		}

		if ( opts ) {
			Editor.pairs( opts, conf.optionsPair, function ( val, label, i, attr ) {
				jqInput.append(
					'<div>'+
						'<input id="'+Editor.safeId( conf.id )+'_'+(i+offset)+'" type="radio" name="'+conf.name+'" />'+
						'<label for="'+Editor.safeId( conf.id )+'_'+(i+offset)+'">'+label+'</label>'+
					'</div>'
				);
				$('input:last', jqInput).attr('value', val)[0]._editor_val = val;

				if ( attr ) {
					$('input:last', jqInput).attr( attr );
				}
			} );
		}
	},


	create: function ( conf ) {
		conf._input = $('<div />');
		fieldTypes.radio._addOptions( conf, conf.options || conf.ipOpts );

		// this is ugly, but IE6/7 has a problem with radio elements that are created
		// and checked before being added to the DOM! Basically it doesn't check them. As
		// such we use the _preChecked property to set cache the checked button and then
		// check it again when the display is shown. This has no effect on other browsers
		// other than to cook a few clock cycles.
		this.on('open', function () {
			conf._input.find('input').each( function () {
				if ( this._preChecked ) {
					this.checked = true;
				}
			} );
		} );

		return conf._input[0];
	},

	get: function ( conf ) {
		var el = conf._input.find('input:checked');
		return el.length ? el[0]._editor_val : undefined;
	},

	set: function ( conf, val ) {
		var that  = this;

		conf._input.find('input').each( function () {
			this._preChecked = false;

			if ( this._editor_val == val ) {
				this.checked = true;
				this._preChecked = true;
			}
			else {
				// In a detached DOM tree, there is no relationship between the
				// input elements, so we need to uncheck any element that does
				// not match the value
				this.checked = false;
				this._preChecked = false;
			}
		} );

		_triggerChange( conf._input.find('input:checked') );
	},

	enable: function ( conf ) {
		conf._input.find('input').prop('disabled', false);
	},

	disable: function ( conf ) {
		conf._input.find('input').prop('disabled', true);
	},

	update: function ( conf, options, append ) {
		var radio = fieldTypes.radio;
		var currVal = radio.get( conf );

		radio._addOptions( conf, options, append );

		// Select the current value if it exists in the new data set, otherwise
		// select the first radio input so there is always a value selected
		var inputs = conf._input.find('input');
		radio.set( conf, inputs.filter('[value="'+currVal+'"]').length ?
			currVal :
			inputs.eq(0).attr('value')
		);
	}
} );


fieldTypes.date = $.extend( true, {}, baseFieldType, {
	create: function ( conf ) {
		conf._input = $('<input />').attr( $.extend( {
			id: Editor.safeId( conf.id ),
			type: 'text'
		}, conf.attr ) );

		if ( $.datepicker ) {
			// jQuery UI date picker
			conf._input.addClass( 'jqueryui' );

			if ( ! conf.dateFormat ) {
				conf.dateFormat = $.datepicker.RFC_2822;
			}

			// Allow the element to be attached to the DOM
			setTimeout( function () {
				$( conf._input ).datepicker( $.extend( {
					showOn: "both",
					dateFormat: conf.dateFormat,
					buttonImage: conf.dateImage,
					buttonImageOnly: true,
					onSelect: function () {
						conf._input.focus().click();
					}
				}, conf.opts ) );

				$('#ui-datepicker-div').css('display','none');
			}, 10 );
		}
		else {
			// HTML5 (only Chrome and Edge on the desktop support this atm)
			conf._input.attr( 'type', 'date' );
		}

		return conf._input[0];
	},

	// use default get method as will work for all

	set: function ( conf, val ) {
		if ( $.datepicker && conf._input.hasClass('hasDatepicker') ) {
			// Due to the async init of the control it is possible that we might
			// try to set a value before it has been initialised!
			conf._input.datepicker( "setDate" , val ).change();
		}
		else {
			$(conf._input).val( val );
		}
	},

	enable: function ( conf ) {
		if ( $.datepicker ) {
			conf._input.datepicker( "enable" );
		}
		else {
			$(conf._input).prop( 'disabled', false );
		}
	},

	disable: function ( conf ) {
		if ( $.datepicker ) {
			conf._input.datepicker( "disable" );
		}
		else {
			$(conf._input).prop( 'disabled', true );
		}
	},

	owns: function ( conf, node ) {
		return $(node).parents('div.ui-datepicker').length || $(node).parents('div.ui-datepicker-header').length ?
			true :
			false;
	}
} );


fieldTypes.datetime = $.extend( true, {}, baseFieldType, {
	create: function ( conf ) {
		conf._input = $('<input />').attr( $.extend( true, {
			id:   Editor.safeId( conf.id ),
			type: 'text'
		}, conf.attr ) );

		conf._picker = new Editor.DateTime( conf._input, $.extend( {
			format: conf.format, // can be undefined
			i18n: this.i18n.datetime,
			onChange: function () {
				_triggerChange( conf._input );
			}
		}, conf.opts ) );

		conf._closeFn = function () {
			conf._picker.hide();
		};
		this.on( 'close', conf._closeFn );

		return conf._input[0];
	},

	// default get, disable and enable options are okay

	set: function ( conf, val ) {
		conf._picker.val( val );

		_triggerChange( conf._input );
	},

	owns: function ( conf, node ) {
		return conf._picker.owns( node );
	},

	errorMessage: function ( conf, msg ) {
		conf._picker.errorMsg( msg );
	},

	destroy: function ( conf ) {
		this.off( 'close', conf._closeFn );
		conf._picker.destroy();
	},

	minDate: function ( conf, min ) {
		conf._picker.min( min );
	},

	maxDate: function ( conf, max ) {
		conf._picker.max( max );
	}
} );


fieldTypes.upload = $.extend( true, {}, baseFieldType, {
	create: function ( conf ) {
		var editor = this;
		var container = _commonUpload( editor, conf, function ( val ) {
			Editor.fieldTypes.upload.set.call( editor, conf, val[0] );
		} );

		return container;
	},

	get: function ( conf ) {
		return conf._val;
	},

	set: function ( conf, val ) {
		conf._val = val;

		var container = conf._input;

		if ( conf.display ) {
			var rendered = container.find('div.rendered');

			if ( conf._val ) {
				rendered.html( conf.display( conf._val ) );
			}
			else {
				rendered
					.empty()
					.append( '<span>'+( conf.noFileText || 'No file' )+'</span>' );
			}
		}

		var button = container.find('div.clearValue button');
		if ( val && conf.clearText ) {
			button.html( conf.clearText );
			container.removeClass( 'noClear' );
		}
		else {
			container.addClass( 'noClear' );
		}

		conf._input.find('input').triggerHandler( 'upload.editor', [ conf._val ] );
	},

	enable: function ( conf ) {
		conf._input.find('input').prop('disabled', false);
		conf._enabled = true;
	},

	disable: function ( conf ) {
		conf._input.find('input').prop('disabled', true);
		conf._enabled = false;
	},

	canReturnSubmit: function ( conf, node ) {
		return false;
	}
} );


fieldTypes.uploadMany = $.extend( true, {}, baseFieldType, {
	create: function ( conf ) {
		var editor = this;
		var container = _commonUpload( editor, conf, function ( val ) {
			conf._val = conf._val.concat( val );
			Editor.fieldTypes.uploadMany.set.call( editor, conf, conf._val );
		} );

		container
			.addClass( 'multi' )
			.on( 'click', 'button.remove', function (e) {
				e.stopPropagation();

				var idx = $(this).data('idx');

				conf._val.splice( idx, 1 );
				Editor.fieldTypes.uploadMany.set.call( editor, conf, conf._val );
			} );

		return container;
	},

	get: function ( conf ) {
		return conf._val;
	},

	set: function ( conf, val ) {
		// Default value for fields is an empty string, whereas we want []
		if ( ! val ) {
			val = [];
		}

		if ( ! $.isArray( val ) ) {
			throw 'Upload collections must have an array as a value';
		}

		conf._val = val;

		var that = this;
		var container = conf._input;

		if ( conf.display ) {
			var rendered = container.find('div.rendered').empty();
			
			if ( val.length ) {
				var list = $('<ul/>').appendTo( rendered );

				$.each( val, function ( i, file ) {
					list.append(
						'<li>'+
							conf.display( file, i )+
							' <button class="'+that.classes.form.button+' remove" data-idx="'+i+'">&times;</button>'+
						'</li>'
					);
				} );
			}
			else {
				rendered.append( '<span>'+( conf.noFileText || 'No files' )+'</span>' );
			}
		}

		conf._input.find('input').triggerHandler( 'upload.editor', [ conf._val ] );
	},

	enable: function ( conf ) {
		conf._input.find('input').prop('disabled', false);
		conf._enabled = true;
	},

	disable: function ( conf ) {
		conf._input.find('input').prop('disabled', true);
		conf._enabled = false;
	},

	canReturnSubmit: function ( conf, node ) {
		return false;
	}
} );


}());


// If there are field types available on DataTables we copy them in (after the
// built in ones to allow overrides) and then expose the field types object.
if ( DataTable.ext.editorFields ) {
	$.extend( Editor.fieldTypes, DataTable.ext.editorFields );
}

DataTable.ext.editorFields = Editor.fieldTypes;


/**
 * File information for uploads
 */
Editor.files = {};


/**
 * Name of this class
 *  @constant CLASS
 *  @type     String
 *  @default  Editor
 */
Editor.prototype.CLASS = "Editor";


/**
 * DataTables Editor version
 *  @constant  Editor.VERSION
 *  @type      String
 *  @default   See code
 *  @static
 */
Editor.version = "1.7.2";


// Event documentation for JSDoc
/**
 * Processing event, fired when Editor submits data to the server for processing.
 * This can be used to provide your own processing indicator if your UI framework
 * already has one.
 *  @name Editor#processing
 *  @event
 *  @param {event} e jQuery event object
 *  @param {boolean} processing Flag for if the processing is running (true) or
 *    not (false).
 */

/**
 * Form displayed event, fired when the form is made available in the DOM. This
 * can be useful for fields that require height and width calculations to be
 * performed since the element is not available in the document until the
 * form is displayed.
 *  @name Editor#open
 *  @event
 *  @param {event} e jQuery event object
 *  @param {string} type Editing type
 */

/**
 * Before a form is displayed, this event is fired. It allows the open action to be
 * cancelled by returning false from the function.
 *  @name Editor#preOpen
 *  @event
 *  @param {event} e jQuery event object
 */

/**
 * Form hidden event, fired when the form is removed from the document. The
 * of the compliment `open` event.
 *  @name Editor#close
 *  @event
 *  @param {event} e jQuery event object
 */

/**
 * Before a form is closed, this event is fired. It allows the close action to be
 * cancelled by returning false from the function. This can be useful for confirming
 * that the user actually wants to close the display (if they have unsaved changes
 * for example).
 *  @name Editor#preClose
 *  @event
 *  @param {event} e jQuery event object
 *  @param {string} trigger Action that caused the close event - can be undefined.
 *    Typically defined by the display controller.
 */

/**
 * Emitted before a form blur occurs. A form blur is similar to a close, but
 * is triggered by a user, typically, clicking on the background, while a close
 * occurs due to a click on the close button. A blur can precede a close.
 *  @name Editor#preBlur
 *  @event
 *  @param {event} e jQuery event object
 */

/**
 * Pre-submit event for the form, fired just before the data is submitted to
 * the server. This event allows you to modify the data that will be submitted
 * to the server. Note that this event runs after the 'formatdata' callback
 * function of the {@link Editor#submit} API method.
 *  @name Editor#preSubmit
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} data The data object that will be submitted to the server
 *  @param {string} action The action type for this submit - `create`, `edit` or
 *    `remove`.
 */

/**
 * Post-submit event for the form, fired immediately after the data has been
 * loaded by the Ajax call, allowing modification or any other interception
 * of the data returned form the server.
 *  @name Editor#postSubmit
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 *  @param {object} data The data object that was be submitted to the server
 *  @param {string} action The action type for this submit - `create`, `edit` or
 *    `remove`.
 */

/**
 * Submission complete event, fired when data has been submitted to the server and
 * after any of the return handling code has been run (updating the DataTable
 * for example). Note that unlike `submitSuccess` and `submitError`, `submitComplete`
 * will be fired for both a successful submission and an error. Additionally this
 * event will be fired after `submitSuccess` or `submitError`.
 *  @name Editor#submitComplete
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 *  @param {object} data The data that was used to update the DataTable
 */

/**
 * Submission complete and successful event, fired when data has been successfully
 * submitted to the server and all actions required by the returned data (inserting
 * or updating a row) have been completed.
 *  @name Editor#submitSuccess
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 *  @param {object} data The data that was used to update the DataTable
 */

/**
 * Submission complete, but in error event, fired when data has been submitted to
 * the server but an error occurred on the server (typically a JSON formatting error)
 *  @name Editor#submitError
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} xhr The Ajax object
 *  @param {string} err The error message from jQuery
 *  @param {object} thrown The exception thrown by jQuery
 *  @param {object} data The data that was used to update the DataTable
 */

/**
 * Create method activated event, fired when the create API method has been called,
 * just prior to the form being shown. Useful for manipulating the form specifically
 * for the create state.
 *  @name Editor#initCreate
 *  @event
 *  @param {event} e jQuery event object
 */

/**
 * Pre-create new row event, fired just before DataTables calls the fnAddData method
 * to add new data to the DataTable, allowing modification of the data that will be
 * used to insert into the table.
 *  @name Editor#preCreate
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 *  @param {object} data The data that will be used to update the DataTable
 */

/**
 * Create new row event, fired when a new row has been created in the DataTable by
 * a form submission. This is called just after the fnAddData call to the DataTable.
 *  @name Editor#create
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 *  @param {object} data The data that was used to update the DataTable
 */

/**
 * As per the `create` event - included for naming consistency.
 *  @name Editor#postCreate
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 *  @param {object} data The data that was used to update the DataTable
 */

/**
 * Edit method activated event, fired when the edit API method has been called,
 * just prior to the form being shown. Useful for manipulating the form specifically
 * for the edit state.
 *  @name Editor#initEdit
 *  @event
 *  @param {event} e jQuery event object
 *  @param {node} tr TR element of the row to be edited
 *  @param {array|object} data Data source array / object for the row to be
 *    edited
 */

/**
 * Pre-edit row event, fired just before DataTables calls the fnUpdate method
 * to edit data in a DataTables row, allowing modification of the data that will be
 * used to update the table.
 *  @name Editor#preEdit
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 *  @param {object} data The data that will be used to update the DataTable
 */

/**
 * Edit row event, fired when a row has been edited in the DataTable by a form
 * submission. This is called just after the fnUpdate call to the DataTable.
 *  @name Editor#edit
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 *  @param {object} data The data that was used to update the DataTable
 */

/**
 * As per the `edit` event - included for naming consistency.
 *  @name Editor#postEdit
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 *  @param {object} data The data that was used to update the DataTable
 */

/**
 * Remove method activated event, fired when the remove API method has been
 * called, just prior to the form being shown. Useful for manipulating the form
 * specifically for the remove state.
 *  @name Editor#initRemove
 *  @event
 *  @param {event} e jQuery event object
 *  @param {array} trs Array of the TR elements for the removed to be deleted
 *  @param {array} data Array of the data source array / objects for the rows to
 *    be deleted. This is in the same index order as the TR nodes in the second
 *    parameter.
 */

/**
 * Pre-remove row event, fired just before DataTables calls the fnDeleteRow method
 * to delete a DataTables row.
 *  @name Editor#preRemove
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 */

/**
 * Row removed event, fired when a row has been removed in the DataTable by a form
 * submission. This is called just after the fnDeleteRow call to the DataTable.
 *  @name Editor#remove
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 */

/**
 * As per the `postRemove` event - included for naming consistency.
 *  @name Editor#postRemove
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 */

/**
 * Set data event, fired when the data is gathered from the form to be used
 * to update the DataTable. This is a "global" version of `preCreate`, `preEdit`
 * and `preRemove` and can be used to manipulate the data that will be added
 * to the DataTable for all three actions
 *  @name Editor#setData
 *  @event
 *  @param {event} e jQuery event object
 *  @param {object} json The JSON object returned from the server
 *  @param {object} data The data that will be used to update the DataTable
 *  @param {string} action The action being performed by the form - 'create',
 *    'edit' or 'remove'.
 */

/**
 * Initialisation of the Editor instance has been completed.
 *  @name Editor#initComplete
 *  @event
 *  @param {event} e jQuery event object
 */


return Editor;
}));
