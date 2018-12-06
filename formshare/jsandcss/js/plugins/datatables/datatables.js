/*
 * This combined file was created by the DataTables downloader builder:
 *   https://datatables.net/download
 *
 * To rebuild or modify this file with the latest versions of the included
 * software please visit:
 *   https://datatables.net/download/#dt/dt-1.10.16/e-1.7.2/b-1.5.1/r-2.2.1
 *
 * Included libraries:
 *   DataTables 1.10.16, Editor 1.7.2, Buttons 1.5.1, Responsive 2.2.1
 */

/*! DataTables 1.10.16
 * ©2008-2017 SpryMedia Ltd - datatables.net/license
 */

/**
 * @summary     DataTables
 * @description Paginate, search and order HTML tables
 * @version     1.10.16
 * @file        jquery.dataTables.js
 * @author      SpryMedia Ltd
 * @contact     www.datatables.net
 * @copyright   Copyright 2008-2017 SpryMedia Ltd.
 *
 * This source file is free software, available under the following license:
 *   MIT license - http://datatables.net/license
 *
 * This source file is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE. See the license files for details.
 *
 * For details please refer to: http://www.datatables.net
 */

/*jslint evil: true, undef: true, browser: true */
/*globals $,require,jQuery,define,_selector_run,_selector_opts,_selector_first,_selector_row_indexes,_ext,_Api,_api_register,_api_registerPlural,_re_new_lines,_re_html,_re_formatted_numeric,_re_escape_regex,_empty,_intVal,_numToDecimal,_isNumber,_isHtml,_htmlNumeric,_pluck,_pluck_order,_range,_stripHtml,_unique,_fnBuildAjax,_fnAjaxUpdate,_fnAjaxParameters,_fnAjaxUpdateDraw,_fnAjaxDataSrc,_fnAddColumn,_fnColumnOptions,_fnAdjustColumnSizing,_fnVisibleToColumnIndex,_fnColumnIndexToVisible,_fnVisbleColumns,_fnGetColumns,_fnColumnTypes,_fnApplyColumnDefs,_fnHungarianMap,_fnCamelToHungarian,_fnLanguageCompat,_fnBrowserDetect,_fnAddData,_fnAddTr,_fnNodeToDataIndex,_fnNodeToColumnIndex,_fnGetCellData,_fnSetCellData,_fnSplitObjNotation,_fnGetObjectDataFn,_fnSetObjectDataFn,_fnGetDataMaster,_fnClearTable,_fnDeleteIndex,_fnInvalidate,_fnGetRowElements,_fnCreateTr,_fnBuildHead,_fnDrawHead,_fnDraw,_fnReDraw,_fnAddOptionsHtml,_fnDetectHeader,_fnGetUniqueThs,_fnFeatureHtmlFilter,_fnFilterComplete,_fnFilterCustom,_fnFilterColumn,_fnFilter,_fnFilterCreateSearch,_fnEscapeRegex,_fnFilterData,_fnFeatureHtmlInfo,_fnUpdateInfo,_fnInfoMacros,_fnInitialise,_fnInitComplete,_fnLengthChange,_fnFeatureHtmlLength,_fnFeatureHtmlPaginate,_fnPageChange,_fnFeatureHtmlProcessing,_fnProcessingDisplay,_fnFeatureHtmlTable,_fnScrollDraw,_fnApplyToChildren,_fnCalculateColumnWidths,_fnThrottle,_fnConvertToWidth,_fnGetWidestNode,_fnGetMaxLenString,_fnStringToCss,_fnSortFlatten,_fnSort,_fnSortAria,_fnSortListener,_fnSortAttachListener,_fnSortingClasses,_fnSortData,_fnSaveState,_fnLoadState,_fnSettingsFromNode,_fnLog,_fnMap,_fnBindAction,_fnCallbackReg,_fnCallbackFire,_fnLengthOverflow,_fnRenderer,_fnDataSource,_fnRowAttributes*/

(function( factory ) {
	"use strict";

	if ( typeof define === 'function' && define.amd ) {
		// AMD
		define( ['jquery'], function ( $ ) {
			return factory( $, window, document );
		} );
	}
	else if ( typeof exports === 'object' ) {
		// CommonJS
		module.exports = function (root, $) {
			if ( ! root ) {
				// CommonJS environments without a window global must pass a
				// root. This will give an error otherwise
				root = window;
			}

			if ( ! $ ) {
				$ = typeof window !== 'undefined' ? // jQuery's factory checks for a global window
					require('jquery') :
					require('jquery')( root );
			}

			return factory( $, root, root.document );
		};
	}
	else {
		// Browser
		factory( jQuery, window, document );
	}
}
(function( $, window, document, undefined ) {
	"use strict";

	/**
	 * DataTables is a plug-in for the jQuery Javascript library. It is a highly
	 * flexible tool, based upon the foundations of progressive enhancement,
	 * which will add advanced interaction controls to any HTML table. For a
	 * full list of features please refer to
	 * [DataTables.net](href="http://datatables.net).
	 *
	 * Note that the `DataTable` object is not a global variable but is aliased
	 * to `jQuery.fn.DataTable` and `jQuery.fn.dataTable` through which it may
	 * be  accessed.
	 *
	 *  @class
	 *  @param {object} [init={}] Configuration object for DataTables. Options
	 *    are defined by {@link DataTable.defaults}
	 *  @requires jQuery 1.7+
	 *
	 *  @example
	 *    // Basic initialisation
	 *    $(document).ready( function {
	 *      $('#example').dataTable();
	 *    } );
	 *
	 *  @example
	 *    // Initialisation with configuration options - in this case, disable
	 *    // pagination and sorting.
	 *    $(document).ready( function {
	 *      $('#example').dataTable( {
	 *        "paginate": false,
	 *        "sort": false
	 *      } );
	 *    } );
	 */
	var DataTable = function ( options )
	{
		/**
		 * Perform a jQuery selector action on the table's TR elements (from the tbody) and
		 * return the resulting jQuery object.
		 *  @param {string|node|jQuery} sSelector jQuery selector or node collection to act on
		 *  @param {object} [oOpts] Optional parameters for modifying the rows to be included
		 *  @param {string} [oOpts.filter=none] Select TR elements that meet the current filter
		 *    criterion ("applied") or all TR elements (i.e. no filter).
		 *  @param {string} [oOpts.order=current] Order of the TR elements in the processed array.
		 *    Can be either 'current', whereby the current sorting of the table is used, or
		 *    'original' whereby the original order the data was read into the table is used.
		 *  @param {string} [oOpts.page=all] Limit the selection to the currently displayed page
		 *    ("current") or not ("all"). If 'current' is given, then order is assumed to be
		 *    'current' and filter is 'applied', regardless of what they might be given as.
		 *  @returns {object} jQuery object, filtered by the given selector.
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *
		 *      // Highlight every second row
		 *      oTable.$('tr:odd').css('backgroundColor', 'blue');
		 *    } );
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *
		 *      // Filter to rows with 'Webkit' in them, add a background colour and then
		 *      // remove the filter, thus highlighting the 'Webkit' rows only.
		 *      oTable.fnFilter('Webkit');
		 *      oTable.$('tr', {"search": "applied"}).css('backgroundColor', 'blue');
		 *      oTable.fnFilter('');
		 *    } );
		 */
		this.$ = function ( sSelector, oOpts )
		{
			return this.api(true).$( sSelector, oOpts );
		};
		
		
		/**
		 * Almost identical to $ in operation, but in this case returns the data for the matched
		 * rows - as such, the jQuery selector used should match TR row nodes or TD/TH cell nodes
		 * rather than any descendants, so the data can be obtained for the row/cell. If matching
		 * rows are found, the data returned is the original data array/object that was used to
		 * create the row (or a generated array if from a DOM source).
		 *
		 * This method is often useful in-combination with $ where both functions are given the
		 * same parameters and the array indexes will match identically.
		 *  @param {string|node|jQuery} sSelector jQuery selector or node collection to act on
		 *  @param {object} [oOpts] Optional parameters for modifying the rows to be included
		 *  @param {string} [oOpts.filter=none] Select elements that meet the current filter
		 *    criterion ("applied") or all elements (i.e. no filter).
		 *  @param {string} [oOpts.order=current] Order of the data in the processed array.
		 *    Can be either 'current', whereby the current sorting of the table is used, or
		 *    'original' whereby the original order the data was read into the table is used.
		 *  @param {string} [oOpts.page=all] Limit the selection to the currently displayed page
		 *    ("current") or not ("all"). If 'current' is given, then order is assumed to be
		 *    'current' and filter is 'applied', regardless of what they might be given as.
		 *  @returns {array} Data for the matched elements. If any elements, as a result of the
		 *    selector, were not TR, TD or TH elements in the DataTable, they will have a null
		 *    entry in the array.
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *
		 *      // Get the data from the first row in the table
		 *      var data = oTable._('tr:first');
		 *
		 *      // Do something useful with the data
		 *      alert( "First cell is: "+data[0] );
		 *    } );
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *
		 *      // Filter to 'Webkit' and get all data for
		 *      oTable.fnFilter('Webkit');
		 *      var data = oTable._('tr', {"search": "applied"});
		 *
		 *      // Do something with the data
		 *      alert( data.length+" rows matched the search" );
		 *    } );
		 */
		this._ = function ( sSelector, oOpts )
		{
			return this.api(true).rows( sSelector, oOpts ).data();
		};
		
		
		/**
		 * Create a DataTables Api instance, with the currently selected tables for
		 * the Api's context.
		 * @param {boolean} [traditional=false] Set the API instance's context to be
		 *   only the table referred to by the `DataTable.ext.iApiIndex` option, as was
		 *   used in the API presented by DataTables 1.9- (i.e. the traditional mode),
		 *   or if all tables captured in the jQuery object should be used.
		 * @return {DataTables.Api}
		 */
		this.api = function ( traditional )
		{
			return traditional ?
				new _Api(
					_fnSettingsFromNode( this[ _ext.iApiIndex ] )
				) :
				new _Api( this );
		};
		
		
		/**
		 * Add a single new row or multiple rows of data to the table. Please note
		 * that this is suitable for client-side processing only - if you are using
		 * server-side processing (i.e. "bServerSide": true), then to add data, you
		 * must add it to the data source, i.e. the server-side, through an Ajax call.
		 *  @param {array|object} data The data to be added to the table. This can be:
		 *    <ul>
		 *      <li>1D array of data - add a single row with the data provided</li>
		 *      <li>2D array of arrays - add multiple rows in a single call</li>
		 *      <li>object - data object when using <i>mData</i></li>
		 *      <li>array of objects - multiple data objects when using <i>mData</i></li>
		 *    </ul>
		 *  @param {bool} [redraw=true] redraw the table or not
		 *  @returns {array} An array of integers, representing the list of indexes in
		 *    <i>aoData</i> ({@link DataTable.models.oSettings}) that have been added to
		 *    the table.
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    // Global var for counter
		 *    var giCount = 2;
		 *
		 *    $(document).ready(function() {
		 *      $('#example').dataTable();
		 *    } );
		 *
		 *    function fnClickAddRow() {
		 *      $('#example').dataTable().fnAddData( [
		 *        giCount+".1",
		 *        giCount+".2",
		 *        giCount+".3",
		 *        giCount+".4" ]
		 *      );
		 *
		 *      giCount++;
		 *    }
		 */
		this.fnAddData = function( data, redraw )
		{
			var api = this.api( true );
		
			/* Check if we want to add multiple rows or not */
			var rows = $.isArray(data) && ( $.isArray(data[0]) || $.isPlainObject(data[0]) ) ?
				api.rows.add( data ) :
				api.row.add( data );
		
			if ( redraw === undefined || redraw ) {
				api.draw();
			}
		
			return rows.flatten().toArray();
		};
		
		
		/**
		 * This function will make DataTables recalculate the column sizes, based on the data
		 * contained in the table and the sizes applied to the columns (in the DOM, CSS or
		 * through the sWidth parameter). This can be useful when the width of the table's
		 * parent element changes (for example a window resize).
		 *  @param {boolean} [bRedraw=true] Redraw the table or not, you will typically want to
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable( {
		 *        "sScrollY": "200px",
		 *        "bPaginate": false
		 *      } );
		 *
		 *      $(window).on('resize', function () {
		 *        oTable.fnAdjustColumnSizing();
		 *      } );
		 *    } );
		 */
		this.fnAdjustColumnSizing = function ( bRedraw )
		{
			var api = this.api( true ).columns.adjust();
			var settings = api.settings()[0];
			var scroll = settings.oScroll;
		
			if ( bRedraw === undefined || bRedraw ) {
				api.draw( false );
			}
			else if ( scroll.sX !== "" || scroll.sY !== "" ) {
				/* If not redrawing, but scrolling, we want to apply the new column sizes anyway */
				_fnScrollDraw( settings );
			}
		};
		
		
		/**
		 * Quickly and simply clear a table
		 *  @param {bool} [bRedraw=true] redraw the table or not
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *
		 *      // Immediately 'nuke' the current rows (perhaps waiting for an Ajax callback...)
		 *      oTable.fnClearTable();
		 *    } );
		 */
		this.fnClearTable = function( bRedraw )
		{
			var api = this.api( true ).clear();
		
			if ( bRedraw === undefined || bRedraw ) {
				api.draw();
			}
		};
		
		
		/**
		 * The exact opposite of 'opening' a row, this function will close any rows which
		 * are currently 'open'.
		 *  @param {node} nTr the table row to 'close'
		 *  @returns {int} 0 on success, or 1 if failed (can't find the row)
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable;
		 *
		 *      // 'open' an information row when a row is clicked on
		 *      $('#example tbody tr').click( function () {
		 *        if ( oTable.fnIsOpen(this) ) {
		 *          oTable.fnClose( this );
		 *        } else {
		 *          oTable.fnOpen( this, "Temporary row opened", "info_row" );
		 *        }
		 *      } );
		 *
		 *      oTable = $('#example').dataTable();
		 *    } );
		 */
		this.fnClose = function( nTr )
		{
			this.api( true ).row( nTr ).child.hide();
		};
		
		
		/**
		 * Remove a row for the table
		 *  @param {mixed} target The index of the row from aoData to be deleted, or
		 *    the TR element you want to delete
		 *  @param {function|null} [callBack] Callback function
		 *  @param {bool} [redraw=true] Redraw the table or not
		 *  @returns {array} The row that was deleted
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *
		 *      // Immediately remove the first row
		 *      oTable.fnDeleteRow( 0 );
		 *    } );
		 */
		this.fnDeleteRow = function( target, callback, redraw )
		{
			var api = this.api( true );
			var rows = api.rows( target );
			var settings = rows.settings()[0];
			var data = settings.aoData[ rows[0][0] ];
		
			rows.remove();
		
			if ( callback ) {
				callback.call( this, settings, data );
			}
		
			if ( redraw === undefined || redraw ) {
				api.draw();
			}
		
			return data;
		};
		
		
		/**
		 * Restore the table to it's original state in the DOM by removing all of DataTables
		 * enhancements, alterations to the DOM structure of the table and event listeners.
		 *  @param {boolean} [remove=false] Completely remove the table from the DOM
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      // This example is fairly pointless in reality, but shows how fnDestroy can be used
		 *      var oTable = $('#example').dataTable();
		 *      oTable.fnDestroy();
		 *    } );
		 */
		this.fnDestroy = function ( remove )
		{
			this.api( true ).destroy( remove );
		};
		
		
		/**
		 * Redraw the table
		 *  @param {bool} [complete=true] Re-filter and resort (if enabled) the table before the draw.
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *
		 *      // Re-draw the table - you wouldn't want to do it here, but it's an example :-)
		 *      oTable.fnDraw();
		 *    } );
		 */
		this.fnDraw = function( complete )
		{
			// Note that this isn't an exact match to the old call to _fnDraw - it takes
			// into account the new data, but can hold position.
			this.api( true ).draw( complete );
		};
		
		
		/**
		 * Filter the input based on data
		 *  @param {string} sInput String to filter the table on
		 *  @param {int|null} [iColumn] Column to limit filtering to
		 *  @param {bool} [bRegex=false] Treat as regular expression or not
		 *  @param {bool} [bSmart=true] Perform smart filtering or not
		 *  @param {bool} [bShowGlobal=true] Show the input global filter in it's input box(es)
		 *  @param {bool} [bCaseInsensitive=true] Do case-insensitive matching (true) or not (false)
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *
		 *      // Sometime later - filter...
		 *      oTable.fnFilter( 'test string' );
		 *    } );
		 */
		this.fnFilter = function( sInput, iColumn, bRegex, bSmart, bShowGlobal, bCaseInsensitive )
		{
			var api = this.api( true );
		
			if ( iColumn === null || iColumn === undefined ) {
				api.search( sInput, bRegex, bSmart, bCaseInsensitive );
			}
			else {
				api.column( iColumn ).search( sInput, bRegex, bSmart, bCaseInsensitive );
			}
		
			api.draw();
		};
		
		
		/**
		 * Get the data for the whole table, an individual row or an individual cell based on the
		 * provided parameters.
		 *  @param {int|node} [src] A TR row node, TD/TH cell node or an integer. If given as
		 *    a TR node then the data source for the whole row will be returned. If given as a
		 *    TD/TH cell node then iCol will be automatically calculated and the data for the
		 *    cell returned. If given as an integer, then this is treated as the aoData internal
		 *    data index for the row (see fnGetPosition) and the data for that row used.
		 *  @param {int} [col] Optional column index that you want the data of.
		 *  @returns {array|object|string} If mRow is undefined, then the data for all rows is
		 *    returned. If mRow is defined, just data for that row, and is iCol is
		 *    defined, only data for the designated cell is returned.
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    // Row data
		 *    $(document).ready(function() {
		 *      oTable = $('#example').dataTable();
		 *
		 *      oTable.$('tr').click( function () {
		 *        var data = oTable.fnGetData( this );
		 *        // ... do something with the array / object of data for the row
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Individual cell data
		 *    $(document).ready(function() {
		 *      oTable = $('#example').dataTable();
		 *
		 *      oTable.$('td').click( function () {
		 *        var sData = oTable.fnGetData( this );
		 *        alert( 'The cell clicked on had the value of '+sData );
		 *      } );
		 *    } );
		 */
		this.fnGetData = function( src, col )
		{
			var api = this.api( true );
		
			if ( src !== undefined ) {
				var type = src.nodeName ? src.nodeName.toLowerCase() : '';
		
				return col !== undefined || type == 'td' || type == 'th' ?
					api.cell( src, col ).data() :
					api.row( src ).data() || null;
			}
		
			return api.data().toArray();
		};
		
		
		/**
		 * Get an array of the TR nodes that are used in the table's body. Note that you will
		 * typically want to use the '$' API method in preference to this as it is more
		 * flexible.
		 *  @param {int} [iRow] Optional row index for the TR element you want
		 *  @returns {array|node} If iRow is undefined, returns an array of all TR elements
		 *    in the table's body, or iRow is defined, just the TR element requested.
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *
		 *      // Get the nodes from the table
		 *      var nNodes = oTable.fnGetNodes( );
		 *    } );
		 */
		this.fnGetNodes = function( iRow )
		{
			var api = this.api( true );
		
			return iRow !== undefined ?
				api.row( iRow ).node() :
				api.rows().nodes().flatten().toArray();
		};
		
		
		/**
		 * Get the array indexes of a particular cell from it's DOM element
		 * and column index including hidden columns
		 *  @param {node} node this can either be a TR, TD or TH in the table's body
		 *  @returns {int} If nNode is given as a TR, then a single index is returned, or
		 *    if given as a cell, an array of [row index, column index (visible),
		 *    column index (all)] is given.
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      $('#example tbody td').click( function () {
		 *        // Get the position of the current data from the node
		 *        var aPos = oTable.fnGetPosition( this );
		 *
		 *        // Get the data array for this row
		 *        var aData = oTable.fnGetData( aPos[0] );
		 *
		 *        // Update the data array and return the value
		 *        aData[ aPos[1] ] = 'clicked';
		 *        this.innerHTML = 'clicked';
		 *      } );
		 *
		 *      // Init DataTables
		 *      oTable = $('#example').dataTable();
		 *    } );
		 */
		this.fnGetPosition = function( node )
		{
			var api = this.api( true );
			var nodeName = node.nodeName.toUpperCase();
		
			if ( nodeName == 'TR' ) {
				return api.row( node ).index();
			}
			else if ( nodeName == 'TD' || nodeName == 'TH' ) {
				var cell = api.cell( node ).index();
		
				return [
					cell.row,
					cell.columnVisible,
					cell.column
				];
			}
			return null;
		};
		
		
		/**
		 * Check to see if a row is 'open' or not.
		 *  @param {node} nTr the table row to check
		 *  @returns {boolean} true if the row is currently open, false otherwise
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable;
		 *
		 *      // 'open' an information row when a row is clicked on
		 *      $('#example tbody tr').click( function () {
		 *        if ( oTable.fnIsOpen(this) ) {
		 *          oTable.fnClose( this );
		 *        } else {
		 *          oTable.fnOpen( this, "Temporary row opened", "info_row" );
		 *        }
		 *      } );
		 *
		 *      oTable = $('#example').dataTable();
		 *    } );
		 */
		this.fnIsOpen = function( nTr )
		{
			return this.api( true ).row( nTr ).child.isShown();
		};
		
		
		/**
		 * This function will place a new row directly after a row which is currently
		 * on display on the page, with the HTML contents that is passed into the
		 * function. This can be used, for example, to ask for confirmation that a
		 * particular record should be deleted.
		 *  @param {node} nTr The table row to 'open'
		 *  @param {string|node|jQuery} mHtml The HTML to put into the row
		 *  @param {string} sClass Class to give the new TD cell
		 *  @returns {node} The row opened. Note that if the table row passed in as the
		 *    first parameter, is not found in the table, this method will silently
		 *    return.
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable;
		 *
		 *      // 'open' an information row when a row is clicked on
		 *      $('#example tbody tr').click( function () {
		 *        if ( oTable.fnIsOpen(this) ) {
		 *          oTable.fnClose( this );
		 *        } else {
		 *          oTable.fnOpen( this, "Temporary row opened", "info_row" );
		 *        }
		 *      } );
		 *
		 *      oTable = $('#example').dataTable();
		 *    } );
		 */
		this.fnOpen = function( nTr, mHtml, sClass )
		{
			return this.api( true )
				.row( nTr )
				.child( mHtml, sClass )
				.show()
				.child()[0];
		};
		
		
		/**
		 * Change the pagination - provides the internal logic for pagination in a simple API
		 * function. With this function you can have a DataTables table go to the next,
		 * previous, first or last pages.
		 *  @param {string|int} mAction Paging action to take: "first", "previous", "next" or "last"
		 *    or page number to jump to (integer), note that page 0 is the first page.
		 *  @param {bool} [bRedraw=true] Redraw the table or not
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *      oTable.fnPageChange( 'next' );
		 *    } );
		 */
		this.fnPageChange = function ( mAction, bRedraw )
		{
			var api = this.api( true ).page( mAction );
		
			if ( bRedraw === undefined || bRedraw ) {
				api.draw(false);
			}
		};
		
		
		/**
		 * Show a particular column
		 *  @param {int} iCol The column whose display should be changed
		 *  @param {bool} bShow Show (true) or hide (false) the column
		 *  @param {bool} [bRedraw=true] Redraw the table or not
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *
		 *      // Hide the second column after initialisation
		 *      oTable.fnSetColumnVis( 1, false );
		 *    } );
		 */
		this.fnSetColumnVis = function ( iCol, bShow, bRedraw )
		{
			var api = this.api( true ).column( iCol ).visible( bShow );
		
			if ( bRedraw === undefined || bRedraw ) {
				api.columns.adjust().draw();
			}
		};
		
		
		/**
		 * Get the settings for a particular table for external manipulation
		 *  @returns {object} DataTables settings object. See
		 *    {@link DataTable.models.oSettings}
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *      var oSettings = oTable.fnSettings();
		 *
		 *      // Show an example parameter from the settings
		 *      alert( oSettings._iDisplayStart );
		 *    } );
		 */
		this.fnSettings = function()
		{
			return _fnSettingsFromNode( this[_ext.iApiIndex] );
		};
		
		
		/**
		 * Sort the table by a particular column
		 *  @param {int} iCol the data index to sort on. Note that this will not match the
		 *    'display index' if you have hidden data entries
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *
		 *      // Sort immediately with columns 0 and 1
		 *      oTable.fnSort( [ [0,'asc'], [1,'asc'] ] );
		 *    } );
		 */
		this.fnSort = function( aaSort )
		{
			this.api( true ).order( aaSort ).draw();
		};
		
		
		/**
		 * Attach a sort listener to an element for a given column
		 *  @param {node} nNode the element to attach the sort listener to
		 *  @param {int} iColumn the column that a click on this node will sort on
		 *  @param {function} [fnCallback] callback function when sort is run
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *
		 *      // Sort on column 1, when 'sorter' is clicked on
		 *      oTable.fnSortListener( document.getElementById('sorter'), 1 );
		 *    } );
		 */
		this.fnSortListener = function( nNode, iColumn, fnCallback )
		{
			this.api( true ).order.listener( nNode, iColumn, fnCallback );
		};
		
		
		/**
		 * Update a table cell or row - this method will accept either a single value to
		 * update the cell with, an array of values with one element for each column or
		 * an object in the same format as the original data source. The function is
		 * self-referencing in order to make the multi column updates easier.
		 *  @param {object|array|string} mData Data to update the cell/row with
		 *  @param {node|int} mRow TR element you want to update or the aoData index
		 *  @param {int} [iColumn] The column to update, give as null or undefined to
		 *    update a whole row.
		 *  @param {bool} [bRedraw=true] Redraw the table or not
		 *  @param {bool} [bAction=true] Perform pre-draw actions or not
		 *  @returns {int} 0 on success, 1 on error
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *      oTable.fnUpdate( 'Example update', 0, 0 ); // Single cell
		 *      oTable.fnUpdate( ['a', 'b', 'c', 'd', 'e'], $('tbody tr')[0] ); // Row
		 *    } );
		 */
		this.fnUpdate = function( mData, mRow, iColumn, bRedraw, bAction )
		{
			var api = this.api( true );
		
			if ( iColumn === undefined || iColumn === null ) {
				api.row( mRow ).data( mData );
			}
			else {
				api.cell( mRow, iColumn ).data( mData );
			}
		
			if ( bAction === undefined || bAction ) {
				api.columns.adjust();
			}
		
			if ( bRedraw === undefined || bRedraw ) {
				api.draw();
			}
			return 0;
		};
		
		
		/**
		 * Provide a common method for plug-ins to check the version of DataTables being used, in order
		 * to ensure compatibility.
		 *  @param {string} sVersion Version string to check for, in the format "X.Y.Z". Note that the
		 *    formats "X" and "X.Y" are also acceptable.
		 *  @returns {boolean} true if this version of DataTables is greater or equal to the required
		 *    version, or false if this version of DataTales is not suitable
		 *  @method
		 *  @dtopt API
		 *  @deprecated Since v1.10
		 *
		 *  @example
		 *    $(document).ready(function() {
		 *      var oTable = $('#example').dataTable();
		 *      alert( oTable.fnVersionCheck( '1.9.0' ) );
		 *    } );
		 */
		this.fnVersionCheck = _ext.fnVersionCheck;
		

		var _that = this;
		var emptyInit = options === undefined;
		var len = this.length;

		if ( emptyInit ) {
			options = {};
		}

		this.oApi = this.internal = _ext.internal;

		// Extend with old style plug-in API methods
		for ( var fn in DataTable.ext.internal ) {
			if ( fn ) {
				this[fn] = _fnExternApiFunc(fn);
			}
		}

		this.each(function() {
			// For each initialisation we want to give it a clean initialisation
			// object that can be bashed around
			var o = {};
			var oInit = len > 1 ? // optimisation for single table case
				_fnExtend( o, options, true ) :
				options;

			/*global oInit,_that,emptyInit*/
			var i=0, iLen, j, jLen, k, kLen;
			var sId = this.getAttribute( 'id' );
			var bInitHandedOff = false;
			var defaults = DataTable.defaults;
			var $this = $(this);
			
			
			/* Sanity check */
			if ( this.nodeName.toLowerCase() != 'table' )
			{
				_fnLog( null, 0, 'Non-table node initialisation ('+this.nodeName+')', 2 );
				return;
			}
			
			/* Backwards compatibility for the defaults */
			_fnCompatOpts( defaults );
			_fnCompatCols( defaults.column );
			
			/* Convert the camel-case defaults to Hungarian */
			_fnCamelToHungarian( defaults, defaults, true );
			_fnCamelToHungarian( defaults.column, defaults.column, true );
			
			/* Setting up the initialisation object */
			_fnCamelToHungarian( defaults, $.extend( oInit, $this.data() ) );
			
			
			
			/* Check to see if we are re-initialising a table */
			var allSettings = DataTable.settings;
			for ( i=0, iLen=allSettings.length ; i<iLen ; i++ )
			{
				var s = allSettings[i];
			
				/* Base check on table node */
				if ( s.nTable == this || s.nTHead.parentNode == this || (s.nTFoot && s.nTFoot.parentNode == this) )
				{
					var bRetrieve = oInit.bRetrieve !== undefined ? oInit.bRetrieve : defaults.bRetrieve;
					var bDestroy = oInit.bDestroy !== undefined ? oInit.bDestroy : defaults.bDestroy;
			
					if ( emptyInit || bRetrieve )
					{
						return s.oInstance;
					}
					else if ( bDestroy )
					{
						s.oInstance.fnDestroy();
						break;
					}
					else
					{
						_fnLog( s, 0, 'Cannot reinitialise DataTable', 3 );
						return;
					}
				}
			
				/* If the element we are initialising has the same ID as a table which was previously
				 * initialised, but the table nodes don't match (from before) then we destroy the old
				 * instance by simply deleting it. This is under the assumption that the table has been
				 * destroyed by other methods. Anyone using non-id selectors will need to do this manually
				 */
				if ( s.sTableId == this.id )
				{
					allSettings.splice( i, 1 );
					break;
				}
			}
			
			/* Ensure the table has an ID - required for accessibility */
			if ( sId === null || sId === "" )
			{
				sId = "DataTables_Table_"+(DataTable.ext._unique++);
				this.id = sId;
			}
			
			/* Create the settings object for this table and set some of the default parameters */
			var oSettings = $.extend( true, {}, DataTable.models.oSettings, {
				"sDestroyWidth": $this[0].style.width,
				"sInstance":     sId,
				"sTableId":      sId
			} );
			oSettings.nTable = this;
			oSettings.oApi   = _that.internal;
			oSettings.oInit  = oInit;
			
			allSettings.push( oSettings );
			
			// Need to add the instance after the instance after the settings object has been added
			// to the settings array, so we can self reference the table instance if more than one
			oSettings.oInstance = (_that.length===1) ? _that : $this.dataTable();
			
			// Backwards compatibility, before we apply all the defaults
			_fnCompatOpts( oInit );
			
			if ( oInit.oLanguage )
			{
				_fnLanguageCompat( oInit.oLanguage );
			}
			
			// If the length menu is given, but the init display length is not, use the length menu
			if ( oInit.aLengthMenu && ! oInit.iDisplayLength )
			{
				oInit.iDisplayLength = $.isArray( oInit.aLengthMenu[0] ) ?
					oInit.aLengthMenu[0][0] : oInit.aLengthMenu[0];
			}
			
			// Apply the defaults and init options to make a single init object will all
			// options defined from defaults and instance options.
			oInit = _fnExtend( $.extend( true, {}, defaults ), oInit );
			
			
			// Map the initialisation options onto the settings object
			_fnMap( oSettings.oFeatures, oInit, [
				"bPaginate",
				"bLengthChange",
				"bFilter",
				"bSort",
				"bSortMulti",
				"bInfo",
				"bProcessing",
				"bAutoWidth",
				"bSortClasses",
				"bServerSide",
				"bDeferRender"
			] );
			_fnMap( oSettings, oInit, [
				"asStripeClasses",
				"ajax",
				"fnServerData",
				"fnFormatNumber",
				"sServerMethod",
				"aaSorting",
				"aaSortingFixed",
				"aLengthMenu",
				"sPaginationType",
				"sAjaxSource",
				"sAjaxDataProp",
				"iStateDuration",
				"sDom",
				"bSortCellsTop",
				"iTabIndex",
				"fnStateLoadCallback",
				"fnStateSaveCallback",
				"renderer",
				"searchDelay",
				"rowId",
				[ "iCookieDuration", "iStateDuration" ], // backwards compat
				[ "oSearch", "oPreviousSearch" ],
				[ "aoSearchCols", "aoPreSearchCols" ],
				[ "iDisplayLength", "_iDisplayLength" ]
			] );
			_fnMap( oSettings.oScroll, oInit, [
				[ "sScrollX", "sX" ],
				[ "sScrollXInner", "sXInner" ],
				[ "sScrollY", "sY" ],
				[ "bScrollCollapse", "bCollapse" ]
			] );
			_fnMap( oSettings.oLanguage, oInit, "fnInfoCallback" );
			
			/* Callback functions which are array driven */
			_fnCallbackReg( oSettings, 'aoDrawCallback',       oInit.fnDrawCallback,      'user' );
			_fnCallbackReg( oSettings, 'aoServerParams',       oInit.fnServerParams,      'user' );
			_fnCallbackReg( oSettings, 'aoStateSaveParams',    oInit.fnStateSaveParams,   'user' );
			_fnCallbackReg( oSettings, 'aoStateLoadParams',    oInit.fnStateLoadParams,   'user' );
			_fnCallbackReg( oSettings, 'aoStateLoaded',        oInit.fnStateLoaded,       'user' );
			_fnCallbackReg( oSettings, 'aoRowCallback',        oInit.fnRowCallback,       'user' );
			_fnCallbackReg( oSettings, 'aoRowCreatedCallback', oInit.fnCreatedRow,        'user' );
			_fnCallbackReg( oSettings, 'aoHeaderCallback',     oInit.fnHeaderCallback,    'user' );
			_fnCallbackReg( oSettings, 'aoFooterCallback',     oInit.fnFooterCallback,    'user' );
			_fnCallbackReg( oSettings, 'aoInitComplete',       oInit.fnInitComplete,      'user' );
			_fnCallbackReg( oSettings, 'aoPreDrawCallback',    oInit.fnPreDrawCallback,   'user' );
			
			oSettings.rowIdFn = _fnGetObjectDataFn( oInit.rowId );
			
			/* Browser support detection */
			_fnBrowserDetect( oSettings );
			
			var oClasses = oSettings.oClasses;
			
			$.extend( oClasses, DataTable.ext.classes, oInit.oClasses );
			$this.addClass( oClasses.sTable );
			
			
			if ( oSettings.iInitDisplayStart === undefined )
			{
				/* Display start point, taking into account the save saving */
				oSettings.iInitDisplayStart = oInit.iDisplayStart;
				oSettings._iDisplayStart = oInit.iDisplayStart;
			}
			
			if ( oInit.iDeferLoading !== null )
			{
				oSettings.bDeferLoading = true;
				var tmp = $.isArray( oInit.iDeferLoading );
				oSettings._iRecordsDisplay = tmp ? oInit.iDeferLoading[0] : oInit.iDeferLoading;
				oSettings._iRecordsTotal = tmp ? oInit.iDeferLoading[1] : oInit.iDeferLoading;
			}
			
			/* Language definitions */
			var oLanguage = oSettings.oLanguage;
			$.extend( true, oLanguage, oInit.oLanguage );
			
			if ( oLanguage.sUrl )
			{
				/* Get the language definitions from a file - because this Ajax call makes the language
				 * get async to the remainder of this function we use bInitHandedOff to indicate that
				 * _fnInitialise will be fired by the returned Ajax handler, rather than the constructor
				 */
				$.ajax( {
					dataType: 'json',
					url: oLanguage.sUrl,
					success: function ( json ) {
						_fnLanguageCompat( json );
						_fnCamelToHungarian( defaults.oLanguage, json );
						$.extend( true, oLanguage, json );
						_fnInitialise( oSettings );
					},
					error: function () {
						// Error occurred loading language file, continue on as best we can
						_fnInitialise( oSettings );
					}
				} );
				bInitHandedOff = true;
			}
			
			/*
			 * Stripes
			 */
			if ( oInit.asStripeClasses === null )
			{
				oSettings.asStripeClasses =[
					oClasses.sStripeOdd,
					oClasses.sStripeEven
				];
			}
			
			/* Remove row stripe classes if they are already on the table row */
			var stripeClasses = oSettings.asStripeClasses;
			var rowOne = $this.children('tbody').find('tr').eq(0);
			if ( $.inArray( true, $.map( stripeClasses, function(el, i) {
				return rowOne.hasClass(el);
			} ) ) !== -1 ) {
				$('tbody tr', this).removeClass( stripeClasses.join(' ') );
				oSettings.asDestroyStripes = stripeClasses.slice();
			}
			
			/*
			 * Columns
			 * See if we should load columns automatically or use defined ones
			 */
			var anThs = [];
			var aoColumnsInit;
			var nThead = this.getElementsByTagName('thead');
			if ( nThead.length !== 0 )
			{
				_fnDetectHeader( oSettings.aoHeader, nThead[0] );
				anThs = _fnGetUniqueThs( oSettings );
			}
			
			/* If not given a column array, generate one with nulls */
			if ( oInit.aoColumns === null )
			{
				aoColumnsInit = [];
				for ( i=0, iLen=anThs.length ; i<iLen ; i++ )
				{
					aoColumnsInit.push( null );
				}
			}
			else
			{
				aoColumnsInit = oInit.aoColumns;
			}
			
			/* Add the columns */
			for ( i=0, iLen=aoColumnsInit.length ; i<iLen ; i++ )
			{
				_fnAddColumn( oSettings, anThs ? anThs[i] : null );
			}
			
			/* Apply the column definitions */
			_fnApplyColumnDefs( oSettings, oInit.aoColumnDefs, aoColumnsInit, function (iCol, oDef) {
				_fnColumnOptions( oSettings, iCol, oDef );
			} );
			
			/* HTML5 attribute detection - build an mData object automatically if the
			 * attributes are found
			 */
			if ( rowOne.length ) {
				var a = function ( cell, name ) {
					return cell.getAttribute( 'data-'+name ) !== null ? name : null;
				};
			
				$( rowOne[0] ).children('th, td').each( function (i, cell) {
					var col = oSettings.aoColumns[i];
			
					if ( col.mData === i ) {
						var sort = a( cell, 'sort' ) || a( cell, 'order' );
						var filter = a( cell, 'filter' ) || a( cell, 'search' );
			
						if ( sort !== null || filter !== null ) {
							col.mData = {
								_:      i+'.display',
								sort:   sort !== null   ? i+'.@data-'+sort   : undefined,
								type:   sort !== null   ? i+'.@data-'+sort   : undefined,
								filter: filter !== null ? i+'.@data-'+filter : undefined
							};
			
							_fnColumnOptions( oSettings, i );
						}
					}
				} );
			}
			
			var features = oSettings.oFeatures;
			var loadedInit = function () {
				/*
				 * Sorting
				 * @todo For modularisation (1.11) this needs to do into a sort start up handler
				 */
			
				// If aaSorting is not defined, then we use the first indicator in asSorting
				// in case that has been altered, so the default sort reflects that option
				if ( oInit.aaSorting === undefined ) {
					var sorting = oSettings.aaSorting;
					for ( i=0, iLen=sorting.length ; i<iLen ; i++ ) {
						sorting[i][1] = oSettings.aoColumns[ i ].asSorting[0];
					}
				}
			
				/* Do a first pass on the sorting classes (allows any size changes to be taken into
				 * account, and also will apply sorting disabled classes if disabled
				 */
				_fnSortingClasses( oSettings );
			
				if ( features.bSort ) {
					_fnCallbackReg( oSettings, 'aoDrawCallback', function () {
						if ( oSettings.bSorted ) {
							var aSort = _fnSortFlatten( oSettings );
							var sortedColumns = {};
			
							$.each( aSort, function (i, val) {
								sortedColumns[ val.src ] = val.dir;
							} );
			
							_fnCallbackFire( oSettings, null, 'order', [oSettings, aSort, sortedColumns] );
							_fnSortAria( oSettings );
						}
					} );
				}
			
				_fnCallbackReg( oSettings, 'aoDrawCallback', function () {
					if ( oSettings.bSorted || _fnDataSource( oSettings ) === 'ssp' || features.bDeferRender ) {
						_fnSortingClasses( oSettings );
					}
				}, 'sc' );
			
			
				/*
				 * Final init
				 * Cache the header, body and footer as required, creating them if needed
				 */
			
				// Work around for Webkit bug 83867 - store the caption-side before removing from doc
				var captions = $this.children('caption').each( function () {
					this._captionSide = $(this).css('caption-side');
				} );
			
				var thead = $this.children('thead');
				if ( thead.length === 0 ) {
					thead = $('<thead/>').appendTo($this);
				}
				oSettings.nTHead = thead[0];
			
				var tbody = $this.children('tbody');
				if ( tbody.length === 0 ) {
					tbody = $('<tbody/>').appendTo($this);
				}
				oSettings.nTBody = tbody[0];
			
				var tfoot = $this.children('tfoot');
				if ( tfoot.length === 0 && captions.length > 0 && (oSettings.oScroll.sX !== "" || oSettings.oScroll.sY !== "") ) {
					// If we are a scrolling table, and no footer has been given, then we need to create
					// a tfoot element for the caption element to be appended to
					tfoot = $('<tfoot/>').appendTo($this);
				}
			
				if ( tfoot.length === 0 || tfoot.children().length === 0 ) {
					$this.addClass( oClasses.sNoFooter );
				}
				else if ( tfoot.length > 0 ) {
					oSettings.nTFoot = tfoot[0];
					_fnDetectHeader( oSettings.aoFooter, oSettings.nTFoot );
				}
			
				/* Check if there is data passing into the constructor */
				if ( oInit.aaData ) {
					for ( i=0 ; i<oInit.aaData.length ; i++ ) {
						_fnAddData( oSettings, oInit.aaData[ i ] );
					}
				}
				else if ( oSettings.bDeferLoading || _fnDataSource( oSettings ) == 'dom' ) {
					/* Grab the data from the page - only do this when deferred loading or no Ajax
					 * source since there is no point in reading the DOM data if we are then going
					 * to replace it with Ajax data
					 */
					_fnAddTr( oSettings, $(oSettings.nTBody).children('tr') );
				}
			
				/* Copy the data index array */
				oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();
			
				/* Initialisation complete - table can be drawn */
				oSettings.bInitialised = true;
			
				/* Check if we need to initialise the table (it might not have been handed off to the
				 * language processor)
				 */
				if ( bInitHandedOff === false ) {
					_fnInitialise( oSettings );
				}
			};
			
			/* Must be done after everything which can be overridden by the state saving! */
			if ( oInit.bStateSave )
			{
				features.bStateSave = true;
				_fnCallbackReg( oSettings, 'aoDrawCallback', _fnSaveState, 'state_save' );
				_fnLoadState( oSettings, oInit, loadedInit );
			}
			else {
				loadedInit();
			}
			
		} );
		_that = null;
		return this;
	};

	
	/*
	 * It is useful to have variables which are scoped locally so only the
	 * DataTables functions can access them and they don't leak into global space.
	 * At the same time these functions are often useful over multiple files in the
	 * core and API, so we list, or at least document, all variables which are used
	 * by DataTables as private variables here. This also ensures that there is no
	 * clashing of variable names and that they can easily referenced for reuse.
	 */
	
	
	// Defined else where
	//  _selector_run
	//  _selector_opts
	//  _selector_first
	//  _selector_row_indexes
	
	var _ext; // DataTable.ext
	var _Api; // DataTable.Api
	var _api_register; // DataTable.Api.register
	var _api_registerPlural; // DataTable.Api.registerPlural
	
	var _re_dic = {};
	var _re_new_lines = /[\r\n]/g;
	var _re_html = /<.*?>/g;
	
	// This is not strict ISO8601 - Date.parse() is quite lax, although
	// implementations differ between browsers.
	var _re_date = /^\d{2,4}[\.\/\-]\d{1,2}[\.\/\-]\d{1,2}([T ]{1}\d{1,2}[:\.]\d{2}([\.:]\d{2})?)?$/;
	
	// Escape regular expression special characters
	var _re_escape_regex = new RegExp( '(\\' + [ '/', '.', '*', '+', '?', '|', '(', ')', '[', ']', '{', '}', '\\', '$', '^', '-' ].join('|\\') + ')', 'g' );
	
	// http://en.wikipedia.org/wiki/Foreign_exchange_market
	// - \u20BD - Russian ruble.
	// - \u20a9 - South Korean Won
	// - \u20BA - Turkish Lira
	// - \u20B9 - Indian Rupee
	// - R - Brazil (R$) and South Africa
	// - fr - Swiss Franc
	// - kr - Swedish krona, Norwegian krone and Danish krone
	// - \u2009 is thin space and \u202F is narrow no-break space, both used in many
	//   standards as thousands separators.
	var _re_formatted_numeric = /[',$£€¥%\u2009\u202F\u20BD\u20a9\u20BArfk]/gi;
	
	
	var _empty = function ( d ) {
		return !d || d === true || d === '-' ? true : false;
	};
	
	
	var _intVal = function ( s ) {
		var integer = parseInt( s, 10 );
		return !isNaN(integer) && isFinite(s) ? integer : null;
	};
	
	// Convert from a formatted number with characters other than `.` as the
	// decimal place, to a Javascript number
	var _numToDecimal = function ( num, decimalPoint ) {
		// Cache created regular expressions for speed as this function is called often
		if ( ! _re_dic[ decimalPoint ] ) {
			_re_dic[ decimalPoint ] = new RegExp( _fnEscapeRegex( decimalPoint ), 'g' );
		}
		return typeof num === 'string' && decimalPoint !== '.' ?
			num.replace( /\./g, '' ).replace( _re_dic[ decimalPoint ], '.' ) :
			num;
	};
	
	
	var _isNumber = function ( d, decimalPoint, formatted ) {
		var strType = typeof d === 'string';
	
		// If empty return immediately so there must be a number if it is a
		// formatted string (this stops the string "k", or "kr", etc being detected
		// as a formatted number for currency
		if ( _empty( d ) ) {
			return true;
		}
	
		if ( decimalPoint && strType ) {
			d = _numToDecimal( d, decimalPoint );
		}
	
		if ( formatted && strType ) {
			d = d.replace( _re_formatted_numeric, '' );
		}
	
		return !isNaN( parseFloat(d) ) && isFinite( d );
	};
	
	
	// A string without HTML in it can be considered to be HTML still
	var _isHtml = function ( d ) {
		return _empty( d ) || typeof d === 'string';
	};
	
	
	var _htmlNumeric = function ( d, decimalPoint, formatted ) {
		if ( _empty( d ) ) {
			return true;
		}
	
		var html = _isHtml( d );
		return ! html ?
			null :
			_isNumber( _stripHtml( d ), decimalPoint, formatted ) ?
				true :
				null;
	};
	
	
	var _pluck = function ( a, prop, prop2 ) {
		var out = [];
		var i=0, ien=a.length;
	
		// Could have the test in the loop for slightly smaller code, but speed
		// is essential here
		if ( prop2 !== undefined ) {
			for ( ; i<ien ; i++ ) {
				if ( a[i] && a[i][ prop ] ) {
					out.push( a[i][ prop ][ prop2 ] );
				}
			}
		}
		else {
			for ( ; i<ien ; i++ ) {
				if ( a[i] ) {
					out.push( a[i][ prop ] );
				}
			}
		}
	
		return out;
	};
	
	
	// Basically the same as _pluck, but rather than looping over `a` we use `order`
	// as the indexes to pick from `a`
	var _pluck_order = function ( a, order, prop, prop2 )
	{
		var out = [];
		var i=0, ien=order.length;
	
		// Could have the test in the loop for slightly smaller code, but speed
		// is essential here
		if ( prop2 !== undefined ) {
			for ( ; i<ien ; i++ ) {
				if ( a[ order[i] ][ prop ] ) {
					out.push( a[ order[i] ][ prop ][ prop2 ] );
				}
			}
		}
		else {
			for ( ; i<ien ; i++ ) {
				out.push( a[ order[i] ][ prop ] );
			}
		}
	
		return out;
	};
	
	
	var _range = function ( len, start )
	{
		var out = [];
		var end;
	
		if ( start === undefined ) {
			start = 0;
			end = len;
		}
		else {
			end = start;
			start = len;
		}
	
		for ( var i=start ; i<end ; i++ ) {
			out.push( i );
		}
	
		return out;
	};
	
	
	var _removeEmpty = function ( a )
	{
		var out = [];
	
		for ( var i=0, ien=a.length ; i<ien ; i++ ) {
			if ( a[i] ) { // careful - will remove all falsy values!
				out.push( a[i] );
			}
		}
	
		return out;
	};
	
	
	var _stripHtml = function ( d ) {
		return d.replace( _re_html, '' );
	};
	
	
	/**
	 * Determine if all values in the array are unique. This means we can short
	 * cut the _unique method at the cost of a single loop. A sorted array is used
	 * to easily check the values.
	 *
	 * @param  {array} src Source array
	 * @return {boolean} true if all unique, false otherwise
	 * @ignore
	 */
	var _areAllUnique = function ( src ) {
		if ( src.length < 2 ) {
			return true;
		}
	
		var sorted = src.slice().sort();
		var last = sorted[0];
	
		for ( var i=1, ien=sorted.length ; i<ien ; i++ ) {
			if ( sorted[i] === last ) {
				return false;
			}
	
			last = sorted[i];
		}
	
		return true;
	};
	
	
	/**
	 * Find the unique elements in a source array.
	 *
	 * @param  {array} src Source array
	 * @return {array} Array of unique items
	 * @ignore
	 */
	var _unique = function ( src )
	{
		if ( _areAllUnique( src ) ) {
			return src.slice();
		}
	
		// A faster unique method is to use object keys to identify used values,
		// but this doesn't work with arrays or objects, which we must also
		// consider. See jsperf.com/compare-array-unique-versions/4 for more
		// information.
		var
			out = [],
			val,
			i, ien=src.length,
			j, k=0;
	
		again: for ( i=0 ; i<ien ; i++ ) {
			val = src[i];
	
			for ( j=0 ; j<k ; j++ ) {
				if ( out[j] === val ) {
					continue again;
				}
			}
	
			out.push( val );
			k++;
		}
	
		return out;
	};
	
	
	/**
	 * DataTables utility methods
	 * 
	 * This namespace provides helper methods that DataTables uses internally to
	 * create a DataTable, but which are not exclusively used only for DataTables.
	 * These methods can be used by extension authors to save the duplication of
	 * code.
	 *
	 *  @namespace
	 */
	DataTable.util = {
		/**
		 * Throttle the calls to a function. Arguments and context are maintained
		 * for the throttled function.
		 *
		 * @param {function} fn Function to be called
		 * @param {integer} freq Call frequency in mS
		 * @return {function} Wrapped function
		 */
		throttle: function ( fn, freq ) {
			var
				frequency = freq !== undefined ? freq : 200,
				last,
				timer;
	
			return function () {
				var
					that = this,
					now  = +new Date(),
					args = arguments;
	
				if ( last && now < last + frequency ) {
					clearTimeout( timer );
	
					timer = setTimeout( function () {
						last = undefined;
						fn.apply( that, args );
					}, frequency );
				}
				else {
					last = now;
					fn.apply( that, args );
				}
			};
		},
	
	
		/**
		 * Escape a string such that it can be used in a regular expression
		 *
		 *  @param {string} val string to escape
		 *  @returns {string} escaped string
		 */
		escapeRegex: function ( val ) {
			return val.replace( _re_escape_regex, '\\$1' );
		}
	};
	
	
	
	/**
	 * Create a mapping object that allows camel case parameters to be looked up
	 * for their Hungarian counterparts. The mapping is stored in a private
	 * parameter called `_hungarianMap` which can be accessed on the source object.
	 *  @param {object} o
	 *  @memberof DataTable#oApi
	 */
	function _fnHungarianMap ( o )
	{
		var
			hungarian = 'a aa ai ao as b fn i m o s ',
			match,
			newKey,
			map = {};
	
		$.each( o, function (key, val) {
			match = key.match(/^([^A-Z]+?)([A-Z])/);
	
			if ( match && hungarian.indexOf(match[1]+' ') !== -1 )
			{
				newKey = key.replace( match[0], match[2].toLowerCase() );
				map[ newKey ] = key;
	
				if ( match[1] === 'o' )
				{
					_fnHungarianMap( o[key] );
				}
			}
		} );
	
		o._hungarianMap = map;
	}
	
	
	/**
	 * Convert from camel case parameters to Hungarian, based on a Hungarian map
	 * created by _fnHungarianMap.
	 *  @param {object} src The model object which holds all parameters that can be
	 *    mapped.
	 *  @param {object} user The object to convert from camel case to Hungarian.
	 *  @param {boolean} force When set to `true`, properties which already have a
	 *    Hungarian value in the `user` object will be overwritten. Otherwise they
	 *    won't be.
	 *  @memberof DataTable#oApi
	 */
	function _fnCamelToHungarian ( src, user, force )
	{
		if ( ! src._hungarianMap ) {
			_fnHungarianMap( src );
		}
	
		var hungarianKey;
	
		$.each( user, function (key, val) {
			hungarianKey = src._hungarianMap[ key ];
	
			if ( hungarianKey !== undefined && (force || user[hungarianKey] === undefined) )
			{
				// For objects, we need to buzz down into the object to copy parameters
				if ( hungarianKey.charAt(0) === 'o' )
				{
					// Copy the camelCase options over to the hungarian
					if ( ! user[ hungarianKey ] ) {
						user[ hungarianKey ] = {};
					}
					$.extend( true, user[hungarianKey], user[key] );
	
					_fnCamelToHungarian( src[hungarianKey], user[hungarianKey], force );
				}
				else {
					user[hungarianKey] = user[ key ];
				}
			}
		} );
	}
	
	
	/**
	 * Language compatibility - when certain options are given, and others aren't, we
	 * need to duplicate the values over, in order to provide backwards compatibility
	 * with older language files.
	 *  @param {object} oSettings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnLanguageCompat( lang )
	{
		var defaults = DataTable.defaults.oLanguage;
		var zeroRecords = lang.sZeroRecords;
	
		/* Backwards compatibility - if there is no sEmptyTable given, then use the same as
		 * sZeroRecords - assuming that is given.
		 */
		if ( ! lang.sEmptyTable && zeroRecords &&
			defaults.sEmptyTable === "No data available in table" )
		{
			_fnMap( lang, lang, 'sZeroRecords', 'sEmptyTable' );
		}
	
		/* Likewise with loading records */
		if ( ! lang.sLoadingRecords && zeroRecords &&
			defaults.sLoadingRecords === "Loading..." )
		{
			_fnMap( lang, lang, 'sZeroRecords', 'sLoadingRecords' );
		}
	
		// Old parameter name of the thousands separator mapped onto the new
		if ( lang.sInfoThousands ) {
			lang.sThousands = lang.sInfoThousands;
		}
	
		var decimal = lang.sDecimal;
		if ( decimal ) {
			_addNumericSort( decimal );
		}
	}
	
	
	/**
	 * Map one parameter onto another
	 *  @param {object} o Object to map
	 *  @param {*} knew The new parameter name
	 *  @param {*} old The old parameter name
	 */
	var _fnCompatMap = function ( o, knew, old ) {
		if ( o[ knew ] !== undefined ) {
			o[ old ] = o[ knew ];
		}
	};
	
	
	/**
	 * Provide backwards compatibility for the main DT options. Note that the new
	 * options are mapped onto the old parameters, so this is an external interface
	 * change only.
	 *  @param {object} init Object to map
	 */
	function _fnCompatOpts ( init )
	{
		_fnCompatMap( init, 'ordering',      'bSort' );
		_fnCompatMap( init, 'orderMulti',    'bSortMulti' );
		_fnCompatMap( init, 'orderClasses',  'bSortClasses' );
		_fnCompatMap( init, 'orderCellsTop', 'bSortCellsTop' );
		_fnCompatMap( init, 'order',         'aaSorting' );
		_fnCompatMap( init, 'orderFixed',    'aaSortingFixed' );
		_fnCompatMap( init, 'paging',        'bPaginate' );
		_fnCompatMap( init, 'pagingType',    'sPaginationType' );
		_fnCompatMap( init, 'pageLength',    'iDisplayLength' );
		_fnCompatMap( init, 'searching',     'bFilter' );
	
		// Boolean initialisation of x-scrolling
		if ( typeof init.sScrollX === 'boolean' ) {
			init.sScrollX = init.sScrollX ? '100%' : '';
		}
		if ( typeof init.scrollX === 'boolean' ) {
			init.scrollX = init.scrollX ? '100%' : '';
		}
	
		// Column search objects are in an array, so it needs to be converted
		// element by element
		var searchCols = init.aoSearchCols;
	
		if ( searchCols ) {
			for ( var i=0, ien=searchCols.length ; i<ien ; i++ ) {
				if ( searchCols[i] ) {
					_fnCamelToHungarian( DataTable.models.oSearch, searchCols[i] );
				}
			}
		}
	}
	
	
	/**
	 * Provide backwards compatibility for column options. Note that the new options
	 * are mapped onto the old parameters, so this is an external interface change
	 * only.
	 *  @param {object} init Object to map
	 */
	function _fnCompatCols ( init )
	{
		_fnCompatMap( init, 'orderable',     'bSortable' );
		_fnCompatMap( init, 'orderData',     'aDataSort' );
		_fnCompatMap( init, 'orderSequence', 'asSorting' );
		_fnCompatMap( init, 'orderDataType', 'sortDataType' );
	
		// orderData can be given as an integer
		var dataSort = init.aDataSort;
		if ( typeof dataSort === 'number' && ! $.isArray( dataSort ) ) {
			init.aDataSort = [ dataSort ];
		}
	}
	
	
	/**
	 * Browser feature detection for capabilities, quirks
	 *  @param {object} settings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnBrowserDetect( settings )
	{
		// We don't need to do this every time DataTables is constructed, the values
		// calculated are specific to the browser and OS configuration which we
		// don't expect to change between initialisations
		if ( ! DataTable.__browser ) {
			var browser = {};
			DataTable.__browser = browser;
	
			// Scrolling feature / quirks detection
			var n = $('<div/>')
				.css( {
					position: 'fixed',
					top: 0,
					left: $(window).scrollLeft()*-1, // allow for scrolling
					height: 1,
					width: 1,
					overflow: 'hidden'
				} )
				.append(
					$('<div/>')
						.css( {
							position: 'absolute',
							top: 1,
							left: 1,
							width: 100,
							overflow: 'scroll'
						} )
						.append(
							$('<div/>')
								.css( {
									width: '100%',
									height: 10
								} )
						)
				)
				.appendTo( 'body' );
	
			var outer = n.children();
			var inner = outer.children();
	
			// Numbers below, in order, are:
			// inner.offsetWidth, inner.clientWidth, outer.offsetWidth, outer.clientWidth
			//
			// IE6 XP:                           100 100 100  83
			// IE7 Vista:                        100 100 100  83
			// IE 8+ Windows:                     83  83 100  83
			// Evergreen Windows:                 83  83 100  83
			// Evergreen Mac with scrollbars:     85  85 100  85
			// Evergreen Mac without scrollbars: 100 100 100 100
	
			// Get scrollbar width
			browser.barWidth = outer[0].offsetWidth - outer[0].clientWidth;
	
			// IE6/7 will oversize a width 100% element inside a scrolling element, to
			// include the width of the scrollbar, while other browsers ensure the inner
			// element is contained without forcing scrolling
			browser.bScrollOversize = inner[0].offsetWidth === 100 && outer[0].clientWidth !== 100;
	
			// In rtl text layout, some browsers (most, but not all) will place the
			// scrollbar on the left, rather than the right.
			browser.bScrollbarLeft = Math.round( inner.offset().left ) !== 1;
	
			// IE8- don't provide height and width for getBoundingClientRect
			browser.bBounding = n[0].getBoundingClientRect().width ? true : false;
	
			n.remove();
		}
	
		$.extend( settings.oBrowser, DataTable.__browser );
		settings.oScroll.iBarWidth = DataTable.__browser.barWidth;
	}
	
	
	/**
	 * Array.prototype reduce[Right] method, used for browsers which don't support
	 * JS 1.6. Done this way to reduce code size, since we iterate either way
	 *  @param {object} settings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnReduce ( that, fn, init, start, end, inc )
	{
		var
			i = start,
			value,
			isSet = false;
	
		if ( init !== undefined ) {
			value = init;
			isSet = true;
		}
	
		while ( i !== end ) {
			if ( ! that.hasOwnProperty(i) ) {
				continue;
			}
	
			value = isSet ?
				fn( value, that[i], i, that ) :
				that[i];
	
			isSet = true;
			i += inc;
		}
	
		return value;
	}
	
	/**
	 * Add a column to the list used for the table with default values
	 *  @param {object} oSettings dataTables settings object
	 *  @param {node} nTh The th element for this column
	 *  @memberof DataTable#oApi
	 */
	function _fnAddColumn( oSettings, nTh )
	{
		// Add column to aoColumns array
		var oDefaults = DataTable.defaults.column;
		var iCol = oSettings.aoColumns.length;
		var oCol = $.extend( {}, DataTable.models.oColumn, oDefaults, {
			"nTh": nTh ? nTh : document.createElement('th'),
			"sTitle":    oDefaults.sTitle    ? oDefaults.sTitle    : nTh ? nTh.innerHTML : '',
			"aDataSort": oDefaults.aDataSort ? oDefaults.aDataSort : [iCol],
			"mData": oDefaults.mData ? oDefaults.mData : iCol,
			idx: iCol
		} );
		oSettings.aoColumns.push( oCol );
	
		// Add search object for column specific search. Note that the `searchCols[ iCol ]`
		// passed into extend can be undefined. This allows the user to give a default
		// with only some of the parameters defined, and also not give a default
		var searchCols = oSettings.aoPreSearchCols;
		searchCols[ iCol ] = $.extend( {}, DataTable.models.oSearch, searchCols[ iCol ] );
	
		// Use the default column options function to initialise classes etc
		_fnColumnOptions( oSettings, iCol, $(nTh).data() );
	}
	
	
	/**
	 * Apply options for a column
	 *  @param {object} oSettings dataTables settings object
	 *  @param {int} iCol column index to consider
	 *  @param {object} oOptions object with sType, bVisible and bSearchable etc
	 *  @memberof DataTable#oApi
	 */
	function _fnColumnOptions( oSettings, iCol, oOptions )
	{
		var oCol = oSettings.aoColumns[ iCol ];
		var oClasses = oSettings.oClasses;
		var th = $(oCol.nTh);
	
		// Try to get width information from the DOM. We can't get it from CSS
		// as we'd need to parse the CSS stylesheet. `width` option can override
		if ( ! oCol.sWidthOrig ) {
			// Width attribute
			oCol.sWidthOrig = th.attr('width') || null;
	
			// Style attribute
			var t = (th.attr('style') || '').match(/width:\s*(\d+[pxem%]+)/);
			if ( t ) {
				oCol.sWidthOrig = t[1];
			}
		}
	
		/* User specified column options */
		if ( oOptions !== undefined && oOptions !== null )
		{
			// Backwards compatibility
			_fnCompatCols( oOptions );
	
			// Map camel case parameters to their Hungarian counterparts
			_fnCamelToHungarian( DataTable.defaults.column, oOptions );
	
			/* Backwards compatibility for mDataProp */
			if ( oOptions.mDataProp !== undefined && !oOptions.mData )
			{
				oOptions.mData = oOptions.mDataProp;
			}
	
			if ( oOptions.sType )
			{
				oCol._sManualType = oOptions.sType;
			}
	
			// `class` is a reserved word in Javascript, so we need to provide
			// the ability to use a valid name for the camel case input
			if ( oOptions.className && ! oOptions.sClass )
			{
				oOptions.sClass = oOptions.className;
			}
			if ( oOptions.sClass ) {
				th.addClass( oOptions.sClass );
			}
	
			$.extend( oCol, oOptions );
			_fnMap( oCol, oOptions, "sWidth", "sWidthOrig" );
	
			/* iDataSort to be applied (backwards compatibility), but aDataSort will take
			 * priority if defined
			 */
			if ( oOptions.iDataSort !== undefined )
			{
				oCol.aDataSort = [ oOptions.iDataSort ];
			}
			_fnMap( oCol, oOptions, "aDataSort" );
		}
	
		/* Cache the data get and set functions for speed */
		var mDataSrc = oCol.mData;
		var mData = _fnGetObjectDataFn( mDataSrc );
		var mRender = oCol.mRender ? _fnGetObjectDataFn( oCol.mRender ) : null;
	
		var attrTest = function( src ) {
			return typeof src === 'string' && src.indexOf('@') !== -1;
		};
		oCol._bAttrSrc = $.isPlainObject( mDataSrc ) && (
			attrTest(mDataSrc.sort) || attrTest(mDataSrc.type) || attrTest(mDataSrc.filter)
		);
		oCol._setter = null;
	
		oCol.fnGetData = function (rowData, type, meta) {
			var innerData = mData( rowData, type, undefined, meta );
	
			return mRender && type ?
				mRender( innerData, type, rowData, meta ) :
				innerData;
		};
		oCol.fnSetData = function ( rowData, val, meta ) {
			return _fnSetObjectDataFn( mDataSrc )( rowData, val, meta );
		};
	
		// Indicate if DataTables should read DOM data as an object or array
		// Used in _fnGetRowElements
		if ( typeof mDataSrc !== 'number' ) {
			oSettings._rowReadObject = true;
		}
	
		/* Feature sorting overrides column specific when off */
		if ( !oSettings.oFeatures.bSort )
		{
			oCol.bSortable = false;
			th.addClass( oClasses.sSortableNone ); // Have to add class here as order event isn't called
		}
	
		/* Check that the class assignment is correct for sorting */
		var bAsc = $.inArray('asc', oCol.asSorting) !== -1;
		var bDesc = $.inArray('desc', oCol.asSorting) !== -1;
		if ( !oCol.bSortable || (!bAsc && !bDesc) )
		{
			oCol.sSortingClass = oClasses.sSortableNone;
			oCol.sSortingClassJUI = "";
		}
		else if ( bAsc && !bDesc )
		{
			oCol.sSortingClass = oClasses.sSortableAsc;
			oCol.sSortingClassJUI = oClasses.sSortJUIAscAllowed;
		}
		else if ( !bAsc && bDesc )
		{
			oCol.sSortingClass = oClasses.sSortableDesc;
			oCol.sSortingClassJUI = oClasses.sSortJUIDescAllowed;
		}
		else
		{
			oCol.sSortingClass = oClasses.sSortable;
			oCol.sSortingClassJUI = oClasses.sSortJUI;
		}
	}
	
	
	/**
	 * Adjust the table column widths for new data. Note: you would probably want to
	 * do a redraw after calling this function!
	 *  @param {object} settings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnAdjustColumnSizing ( settings )
	{
		/* Not interested in doing column width calculation if auto-width is disabled */
		if ( settings.oFeatures.bAutoWidth !== false )
		{
			var columns = settings.aoColumns;
	
			_fnCalculateColumnWidths( settings );
			for ( var i=0 , iLen=columns.length ; i<iLen ; i++ )
			{
				columns[i].nTh.style.width = columns[i].sWidth;
			}
		}
	
		var scroll = settings.oScroll;
		if ( scroll.sY !== '' || scroll.sX !== '')
		{
			_fnScrollDraw( settings );
		}
	
		_fnCallbackFire( settings, null, 'column-sizing', [settings] );
	}
	
	
	/**
	 * Covert the index of a visible column to the index in the data array (take account
	 * of hidden columns)
	 *  @param {object} oSettings dataTables settings object
	 *  @param {int} iMatch Visible column index to lookup
	 *  @returns {int} i the data index
	 *  @memberof DataTable#oApi
	 */
	function _fnVisibleToColumnIndex( oSettings, iMatch )
	{
		var aiVis = _fnGetColumns( oSettings, 'bVisible' );
	
		return typeof aiVis[iMatch] === 'number' ?
			aiVis[iMatch] :
			null;
	}
	
	
	/**
	 * Covert the index of an index in the data array and convert it to the visible
	 *   column index (take account of hidden columns)
	 *  @param {int} iMatch Column index to lookup
	 *  @param {object} oSettings dataTables settings object
	 *  @returns {int} i the data index
	 *  @memberof DataTable#oApi
	 */
	function _fnColumnIndexToVisible( oSettings, iMatch )
	{
		var aiVis = _fnGetColumns( oSettings, 'bVisible' );
		var iPos = $.inArray( iMatch, aiVis );
	
		return iPos !== -1 ? iPos : null;
	}
	
	
	/**
	 * Get the number of visible columns
	 *  @param {object} oSettings dataTables settings object
	 *  @returns {int} i the number of visible columns
	 *  @memberof DataTable#oApi
	 */
	function _fnVisbleColumns( oSettings )
	{
		var vis = 0;
	
		// No reduce in IE8, use a loop for now
		$.each( oSettings.aoColumns, function ( i, col ) {
			if ( col.bVisible && $(col.nTh).css('display') !== 'none' ) {
				vis++;
			}
		} );
	
		return vis;
	}
	
	
	/**
	 * Get an array of column indexes that match a given property
	 *  @param {object} oSettings dataTables settings object
	 *  @param {string} sParam Parameter in aoColumns to look for - typically
	 *    bVisible or bSearchable
	 *  @returns {array} Array of indexes with matched properties
	 *  @memberof DataTable#oApi
	 */
	function _fnGetColumns( oSettings, sParam )
	{
		var a = [];
	
		$.map( oSettings.aoColumns, function(val, i) {
			if ( val[sParam] ) {
				a.push( i );
			}
		} );
	
		return a;
	}
	
	
	/**
	 * Calculate the 'type' of a column
	 *  @param {object} settings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnColumnTypes ( settings )
	{
		var columns = settings.aoColumns;
		var data = settings.aoData;
		var types = DataTable.ext.type.detect;
		var i, ien, j, jen, k, ken;
		var col, cell, detectedType, cache;
	
		// For each column, spin over the 
		for ( i=0, ien=columns.length ; i<ien ; i++ ) {
			col = columns[i];
			cache = [];
	
			if ( ! col.sType && col._sManualType ) {
				col.sType = col._sManualType;
			}
			else if ( ! col.sType ) {
				for ( j=0, jen=types.length ; j<jen ; j++ ) {
					for ( k=0, ken=data.length ; k<ken ; k++ ) {
						// Use a cache array so we only need to get the type data
						// from the formatter once (when using multiple detectors)
						if ( cache[k] === undefined ) {
							cache[k] = _fnGetCellData( settings, k, i, 'type' );
						}
	
						detectedType = types[j]( cache[k], settings );
	
						// If null, then this type can't apply to this column, so
						// rather than testing all cells, break out. There is an
						// exception for the last type which is `html`. We need to
						// scan all rows since it is possible to mix string and HTML
						// types
						if ( ! detectedType && j !== types.length-1 ) {
							break;
						}
	
						// Only a single match is needed for html type since it is
						// bottom of the pile and very similar to string
						if ( detectedType === 'html' ) {
							break;
						}
					}
	
					// Type is valid for all data points in the column - use this
					// type
					if ( detectedType ) {
						col.sType = detectedType;
						break;
					}
				}
	
				// Fall back - if no type was detected, always use string
				if ( ! col.sType ) {
					col.sType = 'string';
				}
			}
		}
	}
	
	
	/**
	 * Take the column definitions and static columns arrays and calculate how
	 * they relate to column indexes. The callback function will then apply the
	 * definition found for a column to a suitable configuration object.
	 *  @param {object} oSettings dataTables settings object
	 *  @param {array} aoColDefs The aoColumnDefs array that is to be applied
	 *  @param {array} aoCols The aoColumns array that defines columns individually
	 *  @param {function} fn Callback function - takes two parameters, the calculated
	 *    column index and the definition for that column.
	 *  @memberof DataTable#oApi
	 */
	function _fnApplyColumnDefs( oSettings, aoColDefs, aoCols, fn )
	{
		var i, iLen, j, jLen, k, kLen, def;
		var columns = oSettings.aoColumns;
	
		// Column definitions with aTargets
		if ( aoColDefs )
		{
			/* Loop over the definitions array - loop in reverse so first instance has priority */
			for ( i=aoColDefs.length-1 ; i>=0 ; i-- )
			{
				def = aoColDefs[i];
	
				/* Each definition can target multiple columns, as it is an array */
				var aTargets = def.targets !== undefined ?
					def.targets :
					def.aTargets;
	
				if ( ! $.isArray( aTargets ) )
				{
					aTargets = [ aTargets ];
				}
	
				for ( j=0, jLen=aTargets.length ; j<jLen ; j++ )
				{
					if ( typeof aTargets[j] === 'number' && aTargets[j] >= 0 )
					{
						/* Add columns that we don't yet know about */
						while( columns.length <= aTargets[j] )
						{
							_fnAddColumn( oSettings );
						}
	
						/* Integer, basic index */
						fn( aTargets[j], def );
					}
					else if ( typeof aTargets[j] === 'number' && aTargets[j] < 0 )
					{
						/* Negative integer, right to left column counting */
						fn( columns.length+aTargets[j], def );
					}
					else if ( typeof aTargets[j] === 'string' )
					{
						/* Class name matching on TH element */
						for ( k=0, kLen=columns.length ; k<kLen ; k++ )
						{
							if ( aTargets[j] == "_all" ||
							     $(columns[k].nTh).hasClass( aTargets[j] ) )
							{
								fn( k, def );
							}
						}
					}
				}
			}
		}
	
		// Statically defined columns array
		if ( aoCols )
		{
			for ( i=0, iLen=aoCols.length ; i<iLen ; i++ )
			{
				fn( i, aoCols[i] );
			}
		}
	}
	
	/**
	 * Add a data array to the table, creating DOM node etc. This is the parallel to
	 * _fnGatherData, but for adding rows from a Javascript source, rather than a
	 * DOM source.
	 *  @param {object} oSettings dataTables settings object
	 *  @param {array} aData data array to be added
	 *  @param {node} [nTr] TR element to add to the table - optional. If not given,
	 *    DataTables will create a row automatically
	 *  @param {array} [anTds] Array of TD|TH elements for the row - must be given
	 *    if nTr is.
	 *  @returns {int} >=0 if successful (index of new aoData entry), -1 if failed
	 *  @memberof DataTable#oApi
	 */
	function _fnAddData ( oSettings, aDataIn, nTr, anTds )
	{
		/* Create the object for storing information about this new row */
		var iRow = oSettings.aoData.length;
		var oData = $.extend( true, {}, DataTable.models.oRow, {
			src: nTr ? 'dom' : 'data',
			idx: iRow
		} );
	
		oData._aData = aDataIn;
		oSettings.aoData.push( oData );
	
		/* Create the cells */
		var nTd, sThisType;
		var columns = oSettings.aoColumns;
	
		// Invalidate the column types as the new data needs to be revalidated
		for ( var i=0, iLen=columns.length ; i<iLen ; i++ )
		{
			columns[i].sType = null;
		}
	
		/* Add to the display array */
		oSettings.aiDisplayMaster.push( iRow );
	
		var id = oSettings.rowIdFn( aDataIn );
		if ( id !== undefined ) {
			oSettings.aIds[ id ] = oData;
		}
	
		/* Create the DOM information, or register it if already present */
		if ( nTr || ! oSettings.oFeatures.bDeferRender )
		{
			_fnCreateTr( oSettings, iRow, nTr, anTds );
		}
	
		return iRow;
	}
	
	
	/**
	 * Add one or more TR elements to the table. Generally we'd expect to
	 * use this for reading data from a DOM sourced table, but it could be
	 * used for an TR element. Note that if a TR is given, it is used (i.e.
	 * it is not cloned).
	 *  @param {object} settings dataTables settings object
	 *  @param {array|node|jQuery} trs The TR element(s) to add to the table
	 *  @returns {array} Array of indexes for the added rows
	 *  @memberof DataTable#oApi
	 */
	function _fnAddTr( settings, trs )
	{
		var row;
	
		// Allow an individual node to be passed in
		if ( ! (trs instanceof $) ) {
			trs = $(trs);
		}
	
		return trs.map( function (i, el) {
			row = _fnGetRowElements( settings, el );
			return _fnAddData( settings, row.data, el, row.cells );
		} );
	}
	
	
	/**
	 * Take a TR element and convert it to an index in aoData
	 *  @param {object} oSettings dataTables settings object
	 *  @param {node} n the TR element to find
	 *  @returns {int} index if the node is found, null if not
	 *  @memberof DataTable#oApi
	 */
	function _fnNodeToDataIndex( oSettings, n )
	{
		return (n._DT_RowIndex!==undefined) ? n._DT_RowIndex : null;
	}
	
	
	/**
	 * Take a TD element and convert it into a column data index (not the visible index)
	 *  @param {object} oSettings dataTables settings object
	 *  @param {int} iRow The row number the TD/TH can be found in
	 *  @param {node} n The TD/TH element to find
	 *  @returns {int} index if the node is found, -1 if not
	 *  @memberof DataTable#oApi
	 */
	function _fnNodeToColumnIndex( oSettings, iRow, n )
	{
		return $.inArray( n, oSettings.aoData[ iRow ].anCells );
	}
	
	
	/**
	 * Get the data for a given cell from the internal cache, taking into account data mapping
	 *  @param {object} settings dataTables settings object
	 *  @param {int} rowIdx aoData row id
	 *  @param {int} colIdx Column index
	 *  @param {string} type data get type ('display', 'type' 'filter' 'sort')
	 *  @returns {*} Cell data
	 *  @memberof DataTable#oApi
	 */
	function _fnGetCellData( settings, rowIdx, colIdx, type )
	{
		var draw           = settings.iDraw;
		var col            = settings.aoColumns[colIdx];
		var rowData        = settings.aoData[rowIdx]._aData;
		var defaultContent = col.sDefaultContent;
		var cellData       = col.fnGetData( rowData, type, {
			settings: settings,
			row:      rowIdx,
			col:      colIdx
		} );
	
		if ( cellData === undefined ) {
			if ( settings.iDrawError != draw && defaultContent === null ) {
				_fnLog( settings, 0, "Requested unknown parameter "+
					(typeof col.mData=='function' ? '{function}' : "'"+col.mData+"'")+
					" for row "+rowIdx+", column "+colIdx, 4 );
				settings.iDrawError = draw;
			}
			return defaultContent;
		}
	
		// When the data source is null and a specific data type is requested (i.e.
		// not the original data), we can use default column data
		if ( (cellData === rowData || cellData === null) && defaultContent !== null && type !== undefined ) {
			cellData = defaultContent;
		}
		else if ( typeof cellData === 'function' ) {
			// If the data source is a function, then we run it and use the return,
			// executing in the scope of the data object (for instances)
			return cellData.call( rowData );
		}
	
		if ( cellData === null && type == 'display' ) {
			return '';
		}
		return cellData;
	}
	
	
	/**
	 * Set the value for a specific cell, into the internal data cache
	 *  @param {object} settings dataTables settings object
	 *  @param {int} rowIdx aoData row id
	 *  @param {int} colIdx Column index
	 *  @param {*} val Value to set
	 *  @memberof DataTable#oApi
	 */
	function _fnSetCellData( settings, rowIdx, colIdx, val )
	{
		var col     = settings.aoColumns[colIdx];
		var rowData = settings.aoData[rowIdx]._aData;
	
		col.fnSetData( rowData, val, {
			settings: settings,
			row:      rowIdx,
			col:      colIdx
		}  );
	}
	
	
	// Private variable that is used to match action syntax in the data property object
	var __reArray = /\[.*?\]$/;
	var __reFn = /\(\)$/;
	
	/**
	 * Split string on periods, taking into account escaped periods
	 * @param  {string} str String to split
	 * @return {array} Split string
	 */
	function _fnSplitObjNotation( str )
	{
		return $.map( str.match(/(\\.|[^\.])+/g) || [''], function ( s ) {
			return s.replace(/\\\./g, '.');
		} );
	}
	
	
	/**
	 * Return a function that can be used to get data from a source object, taking
	 * into account the ability to use nested objects as a source
	 *  @param {string|int|function} mSource The data source for the object
	 *  @returns {function} Data get function
	 *  @memberof DataTable#oApi
	 */
	function _fnGetObjectDataFn( mSource )
	{
		if ( $.isPlainObject( mSource ) )
		{
			/* Build an object of get functions, and wrap them in a single call */
			var o = {};
			$.each( mSource, function (key, val) {
				if ( val ) {
					o[key] = _fnGetObjectDataFn( val );
				}
			} );
	
			return function (data, type, row, meta) {
				var t = o[type] || o._;
				return t !== undefined ?
					t(data, type, row, meta) :
					data;
			};
		}
		else if ( mSource === null )
		{
			/* Give an empty string for rendering / sorting etc */
			return function (data) { // type, row and meta also passed, but not used
				return data;
			};
		}
		else if ( typeof mSource === 'function' )
		{
			return function (data, type, row, meta) {
				return mSource( data, type, row, meta );
			};
		}
		else if ( typeof mSource === 'string' && (mSource.indexOf('.') !== -1 ||
			      mSource.indexOf('[') !== -1 || mSource.indexOf('(') !== -1) )
		{
			/* If there is a . in the source string then the data source is in a
			 * nested object so we loop over the data for each level to get the next
			 * level down. On each loop we test for undefined, and if found immediately
			 * return. This allows entire objects to be missing and sDefaultContent to
			 * be used if defined, rather than throwing an error
			 */
			var fetchData = function (data, type, src) {
				var arrayNotation, funcNotation, out, innerSrc;
	
				if ( src !== "" )
				{
					var a = _fnSplitObjNotation( src );
	
					for ( var i=0, iLen=a.length ; i<iLen ; i++ )
					{
						// Check if we are dealing with special notation
						arrayNotation = a[i].match(__reArray);
						funcNotation = a[i].match(__reFn);
	
						if ( arrayNotation )
						{
							// Array notation
							a[i] = a[i].replace(__reArray, '');
	
							// Condition allows simply [] to be passed in
							if ( a[i] !== "" ) {
								data = data[ a[i] ];
							}
							out = [];
	
							// Get the remainder of the nested object to get
							a.splice( 0, i+1 );
							innerSrc = a.join('.');
	
							// Traverse each entry in the array getting the properties requested
							if ( $.isArray( data ) ) {
								for ( var j=0, jLen=data.length ; j<jLen ; j++ ) {
									out.push( fetchData( data[j], type, innerSrc ) );
								}
							}
	
							// If a string is given in between the array notation indicators, that
							// is used to join the strings together, otherwise an array is returned
							var join = arrayNotation[0].substring(1, arrayNotation[0].length-1);
							data = (join==="") ? out : out.join(join);
	
							// The inner call to fetchData has already traversed through the remainder
							// of the source requested, so we exit from the loop
							break;
						}
						else if ( funcNotation )
						{
							// Function call
							a[i] = a[i].replace(__reFn, '');
							data = data[ a[i] ]();
							continue;
						}
	
						if ( data === null || data[ a[i] ] === undefined )
						{
							return undefined;
						}
						data = data[ a[i] ];
					}
				}
	
				return data;
			};
	
			return function (data, type) { // row and meta also passed, but not used
				return fetchData( data, type, mSource );
			};
		}
		else
		{
			/* Array or flat object mapping */
			return function (data, type) { // row and meta also passed, but not used
				return data[mSource];
			};
		}
	}
	
	
	/**
	 * Return a function that can be used to set data from a source object, taking
	 * into account the ability to use nested objects as a source
	 *  @param {string|int|function} mSource The data source for the object
	 *  @returns {function} Data set function
	 *  @memberof DataTable#oApi
	 */
	function _fnSetObjectDataFn( mSource )
	{
		if ( $.isPlainObject( mSource ) )
		{
			/* Unlike get, only the underscore (global) option is used for for
			 * setting data since we don't know the type here. This is why an object
			 * option is not documented for `mData` (which is read/write), but it is
			 * for `mRender` which is read only.
			 */
			return _fnSetObjectDataFn( mSource._ );
		}
		else if ( mSource === null )
		{
			/* Nothing to do when the data source is null */
			return function () {};
		}
		else if ( typeof mSource === 'function' )
		{
			return function (data, val, meta) {
				mSource( data, 'set', val, meta );
			};
		}
		else if ( typeof mSource === 'string' && (mSource.indexOf('.') !== -1 ||
			      mSource.indexOf('[') !== -1 || mSource.indexOf('(') !== -1) )
		{
			/* Like the get, we need to get data from a nested object */
			var setData = function (data, val, src) {
				var a = _fnSplitObjNotation( src ), b;
				var aLast = a[a.length-1];
				var arrayNotation, funcNotation, o, innerSrc;
	
				for ( var i=0, iLen=a.length-1 ; i<iLen ; i++ )
				{
					// Check if we are dealing with an array notation request
					arrayNotation = a[i].match(__reArray);
					funcNotation = a[i].match(__reFn);
	
					if ( arrayNotation )
					{
						a[i] = a[i].replace(__reArray, '');
						data[ a[i] ] = [];
	
						// Get the remainder of the nested object to set so we can recurse
						b = a.slice();
						b.splice( 0, i+1 );
						innerSrc = b.join('.');
	
						// Traverse each entry in the array setting the properties requested
						if ( $.isArray( val ) )
						{
							for ( var j=0, jLen=val.length ; j<jLen ; j++ )
							{
								o = {};
								setData( o, val[j], innerSrc );
								data[ a[i] ].push( o );
							}
						}
						else
						{
							// We've been asked to save data to an array, but it
							// isn't array data to be saved. Best that can be done
							// is to just save the value.
							data[ a[i] ] = val;
						}
	
						// The inner call to setData has already traversed through the remainder
						// of the source and has set the data, thus we can exit here
						return;
					}
					else if ( funcNotation )
					{
						// Function call
						a[i] = a[i].replace(__reFn, '');
						data = data[ a[i] ]( val );
					}
	
					// If the nested object doesn't currently exist - since we are
					// trying to set the value - create it
					if ( data[ a[i] ] === null || data[ a[i] ] === undefined )
					{
						data[ a[i] ] = {};
					}
					data = data[ a[i] ];
				}
	
				// Last item in the input - i.e, the actual set
				if ( aLast.match(__reFn ) )
				{
					// Function call
					data = data[ aLast.replace(__reFn, '') ]( val );
				}
				else
				{
					// If array notation is used, we just want to strip it and use the property name
					// and assign the value. If it isn't used, then we get the result we want anyway
					data[ aLast.replace(__reArray, '') ] = val;
				}
			};
	
			return function (data, val) { // meta is also passed in, but not used
				return setData( data, val, mSource );
			};
		}
		else
		{
			/* Array or flat object mapping */
			return function (data, val) { // meta is also passed in, but not used
				data[mSource] = val;
			};
		}
	}
	
	
	/**
	 * Return an array with the full table data
	 *  @param {object} oSettings dataTables settings object
	 *  @returns array {array} aData Master data array
	 *  @memberof DataTable#oApi
	 */
	function _fnGetDataMaster ( settings )
	{
		return _pluck( settings.aoData, '_aData' );
	}
	
	
	/**
	 * Nuke the table
	 *  @param {object} oSettings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnClearTable( settings )
	{
		settings.aoData.length = 0;
		settings.aiDisplayMaster.length = 0;
		settings.aiDisplay.length = 0;
		settings.aIds = {};
	}
	
	
	 /**
	 * Take an array of integers (index array) and remove a target integer (value - not
	 * the key!)
	 *  @param {array} a Index array to target
	 *  @param {int} iTarget value to find
	 *  @memberof DataTable#oApi
	 */
	function _fnDeleteIndex( a, iTarget, splice )
	{
		var iTargetIndex = -1;
	
		for ( var i=0, iLen=a.length ; i<iLen ; i++ )
		{
			if ( a[i] == iTarget )
			{
				iTargetIndex = i;
			}
			else if ( a[i] > iTarget )
			{
				a[i]--;
			}
		}
	
		if ( iTargetIndex != -1 && splice === undefined )
		{
			a.splice( iTargetIndex, 1 );
		}
	}
	
	
	/**
	 * Mark cached data as invalid such that a re-read of the data will occur when
	 * the cached data is next requested. Also update from the data source object.
	 *
	 * @param {object} settings DataTables settings object
	 * @param {int}    rowIdx   Row index to invalidate
	 * @param {string} [src]    Source to invalidate from: undefined, 'auto', 'dom'
	 *     or 'data'
	 * @param {int}    [colIdx] Column index to invalidate. If undefined the whole
	 *     row will be invalidated
	 * @memberof DataTable#oApi
	 *
	 * @todo For the modularisation of v1.11 this will need to become a callback, so
	 *   the sort and filter methods can subscribe to it. That will required
	 *   initialisation options for sorting, which is why it is not already baked in
	 */
	function _fnInvalidate( settings, rowIdx, src, colIdx )
	{
		var row = settings.aoData[ rowIdx ];
		var i, ien;
		var cellWrite = function ( cell, col ) {
			// This is very frustrating, but in IE if you just write directly
			// to innerHTML, and elements that are overwritten are GC'ed,
			// even if there is a reference to them elsewhere
			while ( cell.childNodes.length ) {
				cell.removeChild( cell.firstChild );
			}
	
			cell.innerHTML = _fnGetCellData( settings, rowIdx, col, 'display' );
		};
	
		// Are we reading last data from DOM or the data object?
		if ( src === 'dom' || ((! src || src === 'auto') && row.src === 'dom') ) {
			// Read the data from the DOM
			row._aData = _fnGetRowElements(
					settings, row, colIdx, colIdx === undefined ? undefined : row._aData
				)
				.data;
		}
		else {
			// Reading from data object, update the DOM
			var cells = row.anCells;
	
			if ( cells ) {
				if ( colIdx !== undefined ) {
					cellWrite( cells[colIdx], colIdx );
				}
				else {
					for ( i=0, ien=cells.length ; i<ien ; i++ ) {
						cellWrite( cells[i], i );
					}
				}
			}
		}
	
		// For both row and cell invalidation, the cached data for sorting and
		// filtering is nulled out
		row._aSortData = null;
		row._aFilterData = null;
	
		// Invalidate the type for a specific column (if given) or all columns since
		// the data might have changed
		var cols = settings.aoColumns;
		if ( colIdx !== undefined ) {
			cols[ colIdx ].sType = null;
		}
		else {
			for ( i=0, ien=cols.length ; i<ien ; i++ ) {
				cols[i].sType = null;
			}
	
			// Update DataTables special `DT_*` attributes for the row
			_fnRowAttributes( settings, row );
		}
	}
	
	
	/**
	 * Build a data source object from an HTML row, reading the contents of the
	 * cells that are in the row.
	 *
	 * @param {object} settings DataTables settings object
	 * @param {node|object} TR element from which to read data or existing row
	 *   object from which to re-read the data from the cells
	 * @param {int} [colIdx] Optional column index
	 * @param {array|object} [d] Data source object. If `colIdx` is given then this
	 *   parameter should also be given and will be used to write the data into.
	 *   Only the column in question will be written
	 * @returns {object} Object with two parameters: `data` the data read, in
	 *   document order, and `cells` and array of nodes (they can be useful to the
	 *   caller, so rather than needing a second traversal to get them, just return
	 *   them from here).
	 * @memberof DataTable#oApi
	 */
	function _fnGetRowElements( settings, row, colIdx, d )
	{
		var
			tds = [],
			td = row.firstChild,
			name, col, o, i=0, contents,
			columns = settings.aoColumns,
			objectRead = settings._rowReadObject;
	
		// Allow the data object to be passed in, or construct
		d = d !== undefined ?
			d :
			objectRead ?
				{} :
				[];
	
		var attr = function ( str, td  ) {
			if ( typeof str === 'string' ) {
				var idx = str.indexOf('@');
	
				if ( idx !== -1 ) {
					var attr = str.substring( idx+1 );
					var setter = _fnSetObjectDataFn( str );
					setter( d, td.getAttribute( attr ) );
				}
			}
		};
	
		// Read data from a cell and store into the data object
		var cellProcess = function ( cell ) {
			if ( colIdx === undefined || colIdx === i ) {
				col = columns[i];
				contents = $.trim(cell.innerHTML);
	
				if ( col && col._bAttrSrc ) {
					var setter = _fnSetObjectDataFn( col.mData._ );
					setter( d, contents );
	
					attr( col.mData.sort, cell );
					attr( col.mData.type, cell );
					attr( col.mData.filter, cell );
				}
				else {
					// Depending on the `data` option for the columns the data can
					// be read to either an object or an array.
					if ( objectRead ) {
						if ( ! col._setter ) {
							// Cache the setter function
							col._setter = _fnSetObjectDataFn( col.mData );
						}
						col._setter( d, contents );
					}
					else {
						d[i] = contents;
					}
				}
			}
	
			i++;
		};
	
		if ( td ) {
			// `tr` element was passed in
			while ( td ) {
				name = td.nodeName.toUpperCase();
	
				if ( name == "TD" || name == "TH" ) {
					cellProcess( td );
					tds.push( td );
				}
	
				td = td.nextSibling;
			}
		}
		else {
			// Existing row object passed in
			tds = row.anCells;
	
			for ( var j=0, jen=tds.length ; j<jen ; j++ ) {
				cellProcess( tds[j] );
			}
		}
	
		// Read the ID from the DOM if present
		var rowNode = row.firstChild ? row : row.nTr;
	
		if ( rowNode ) {
			var id = rowNode.getAttribute( 'id' );
	
			if ( id ) {
				_fnSetObjectDataFn( settings.rowId )( d, id );
			}
		}
	
		return {
			data: d,
			cells: tds
		};
	}
	/**
	 * Create a new TR element (and it's TD children) for a row
	 *  @param {object} oSettings dataTables settings object
	 *  @param {int} iRow Row to consider
	 *  @param {node} [nTrIn] TR element to add to the table - optional. If not given,
	 *    DataTables will create a row automatically
	 *  @param {array} [anTds] Array of TD|TH elements for the row - must be given
	 *    if nTr is.
	 *  @memberof DataTable#oApi
	 */
	function _fnCreateTr ( oSettings, iRow, nTrIn, anTds )
	{
		var
			row = oSettings.aoData[iRow],
			rowData = row._aData,
			cells = [],
			nTr, nTd, oCol,
			i, iLen;
	
		if ( row.nTr === null )
		{
			nTr = nTrIn || document.createElement('tr');
	
			row.nTr = nTr;
			row.anCells = cells;
	
			/* Use a private property on the node to allow reserve mapping from the node
			 * to the aoData array for fast look up
			 */
			nTr._DT_RowIndex = iRow;
	
			/* Special parameters can be given by the data source to be used on the row */
			_fnRowAttributes( oSettings, row );
	
			/* Process each column */
			for ( i=0, iLen=oSettings.aoColumns.length ; i<iLen ; i++ )
			{
				oCol = oSettings.aoColumns[i];
	
				nTd = nTrIn ? anTds[i] : document.createElement( oCol.sCellType );
				nTd._DT_CellIndex = {
					row: iRow,
					column: i
				};
				
				cells.push( nTd );
	
				// Need to create the HTML if new, or if a rendering function is defined
				if ( (!nTrIn || oCol.mRender || oCol.mData !== i) &&
					 (!$.isPlainObject(oCol.mData) || oCol.mData._ !== i+'.display')
				) {
					nTd.innerHTML = _fnGetCellData( oSettings, iRow, i, 'display' );
				}
	
				/* Add user defined class */
				if ( oCol.sClass )
				{
					nTd.className += ' '+oCol.sClass;
				}
	
				// Visibility - add or remove as required
				if ( oCol.bVisible && ! nTrIn )
				{
					nTr.appendChild( nTd );
				}
				else if ( ! oCol.bVisible && nTrIn )
				{
					nTd.parentNode.removeChild( nTd );
				}
	
				if ( oCol.fnCreatedCell )
				{
					oCol.fnCreatedCell.call( oSettings.oInstance,
						nTd, _fnGetCellData( oSettings, iRow, i ), rowData, iRow, i
					);
				}
			}
	
			_fnCallbackFire( oSettings, 'aoRowCreatedCallback', null, [nTr, rowData, iRow] );
		}
	
		// Remove once webkit bug 131819 and Chromium bug 365619 have been resolved
		// and deployed
		row.nTr.setAttribute( 'role', 'row' );
	}
	
	
	/**
	 * Add attributes to a row based on the special `DT_*` parameters in a data
	 * source object.
	 *  @param {object} settings DataTables settings object
	 *  @param {object} DataTables row object for the row to be modified
	 *  @memberof DataTable#oApi
	 */
	function _fnRowAttributes( settings, row )
	{
		var tr = row.nTr;
		var data = row._aData;
	
		if ( tr ) {
			var id = settings.rowIdFn( data );
	
			if ( id ) {
				tr.id = id;
			}
	
			if ( data.DT_RowClass ) {
				// Remove any classes added by DT_RowClass before
				var a = data.DT_RowClass.split(' ');
				row.__rowc = row.__rowc ?
					_unique( row.__rowc.concat( a ) ) :
					a;
	
				$(tr)
					.removeClass( row.__rowc.join(' ') )
					.addClass( data.DT_RowClass );
			}
	
			if ( data.DT_RowAttr ) {
				$(tr).attr( data.DT_RowAttr );
			}
	
			if ( data.DT_RowData ) {
				$(tr).data( data.DT_RowData );
			}
		}
	}
	
	
	/**
	 * Create the HTML header for the table
	 *  @param {object} oSettings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnBuildHead( oSettings )
	{
		var i, ien, cell, row, column;
		var thead = oSettings.nTHead;
		var tfoot = oSettings.nTFoot;
		var createHeader = $('th, td', thead).length === 0;
		var classes = oSettings.oClasses;
		var columns = oSettings.aoColumns;
	
		if ( createHeader ) {
			row = $('<tr/>').appendTo( thead );
		}
	
		for ( i=0, ien=columns.length ; i<ien ; i++ ) {
			column = columns[i];
			cell = $( column.nTh ).addClass( column.sClass );
	
			if ( createHeader ) {
				cell.appendTo( row );
			}
	
			// 1.11 move into sorting
			if ( oSettings.oFeatures.bSort ) {
				cell.addClass( column.sSortingClass );
	
				if ( column.bSortable !== false ) {
					cell
						.attr( 'tabindex', oSettings.iTabIndex )
						.attr( 'aria-controls', oSettings.sTableId );
	
					_fnSortAttachListener( oSettings, column.nTh, i );
				}
			}
	
			if ( column.sTitle != cell[0].innerHTML ) {
				cell.html( column.sTitle );
			}
	
			_fnRenderer( oSettings, 'header' )(
				oSettings, cell, column, classes
			);
		}
	
		if ( createHeader ) {
			_fnDetectHeader( oSettings.aoHeader, thead );
		}
		
		/* ARIA role for the rows */
	 	$(thead).find('>tr').attr('role', 'row');
	
		/* Deal with the footer - add classes if required */
		$(thead).find('>tr>th, >tr>td').addClass( classes.sHeaderTH );
		$(tfoot).find('>tr>th, >tr>td').addClass( classes.sFooterTH );
	
		// Cache the footer cells. Note that we only take the cells from the first
		// row in the footer. If there is more than one row the user wants to
		// interact with, they need to use the table().foot() method. Note also this
		// allows cells to be used for multiple columns using colspan
		if ( tfoot !== null ) {
			var cells = oSettings.aoFooter[0];
	
			for ( i=0, ien=cells.length ; i<ien ; i++ ) {
				column = columns[i];
				column.nTf = cells[i].cell;
	
				if ( column.sClass ) {
					$(column.nTf).addClass( column.sClass );
				}
			}
		}
	}
	
	
	/**
	 * Draw the header (or footer) element based on the column visibility states. The
	 * methodology here is to use the layout array from _fnDetectHeader, modified for
	 * the instantaneous column visibility, to construct the new layout. The grid is
	 * traversed over cell at a time in a rows x columns grid fashion, although each
	 * cell insert can cover multiple elements in the grid - which is tracks using the
	 * aApplied array. Cell inserts in the grid will only occur where there isn't
	 * already a cell in that position.
	 *  @param {object} oSettings dataTables settings object
	 *  @param array {objects} aoSource Layout array from _fnDetectHeader
	 *  @param {boolean} [bIncludeHidden=false] If true then include the hidden columns in the calc,
	 *  @memberof DataTable#oApi
	 */
	function _fnDrawHead( oSettings, aoSource, bIncludeHidden )
	{
		var i, iLen, j, jLen, k, kLen, n, nLocalTr;
		var aoLocal = [];
		var aApplied = [];
		var iColumns = oSettings.aoColumns.length;
		var iRowspan, iColspan;
	
		if ( ! aoSource )
		{
			return;
		}
	
		if (  bIncludeHidden === undefined )
		{
			bIncludeHidden = false;
		}
	
		/* Make a copy of the master layout array, but without the visible columns in it */
		for ( i=0, iLen=aoSource.length ; i<iLen ; i++ )
		{
			aoLocal[i] = aoSource[i].slice();
			aoLocal[i].nTr = aoSource[i].nTr;
	
			/* Remove any columns which are currently hidden */
			for ( j=iColumns-1 ; j>=0 ; j-- )
			{
				if ( !oSettings.aoColumns[j].bVisible && !bIncludeHidden )
				{
					aoLocal[i].splice( j, 1 );
				}
			}
	
			/* Prep the applied array - it needs an element for each row */
			aApplied.push( [] );
		}
	
		for ( i=0, iLen=aoLocal.length ; i<iLen ; i++ )
		{
			nLocalTr = aoLocal[i].nTr;
	
			/* All cells are going to be replaced, so empty out the row */
			if ( nLocalTr )
			{
				while( (n = nLocalTr.firstChild) )
				{
					nLocalTr.removeChild( n );
				}
			}
	
			for ( j=0, jLen=aoLocal[i].length ; j<jLen ; j++ )
			{
				iRowspan = 1;
				iColspan = 1;
	
				/* Check to see if there is already a cell (row/colspan) covering our target
				 * insert point. If there is, then there is nothing to do.
				 */
				if ( aApplied[i][j] === undefined )
				{
					nLocalTr.appendChild( aoLocal[i][j].cell );
					aApplied[i][j] = 1;
	
					/* Expand the cell to cover as many rows as needed */
					while ( aoLocal[i+iRowspan] !== undefined &&
					        aoLocal[i][j].cell == aoLocal[i+iRowspan][j].cell )
					{
						aApplied[i+iRowspan][j] = 1;
						iRowspan++;
					}
	
					/* Expand the cell to cover as many columns as needed */
					while ( aoLocal[i][j+iColspan] !== undefined &&
					        aoLocal[i][j].cell == aoLocal[i][j+iColspan].cell )
					{
						/* Must update the applied array over the rows for the columns */
						for ( k=0 ; k<iRowspan ; k++ )
						{
							aApplied[i+k][j+iColspan] = 1;
						}
						iColspan++;
					}
	
					/* Do the actual expansion in the DOM */
					$(aoLocal[i][j].cell)
						.attr('rowspan', iRowspan)
						.attr('colspan', iColspan);
				}
			}
		}
	}
	
	
	/**
	 * Insert the required TR nodes into the table for display
	 *  @param {object} oSettings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnDraw( oSettings )
	{
		/* Provide a pre-callback function which can be used to cancel the draw is false is returned */
		var aPreDraw = _fnCallbackFire( oSettings, 'aoPreDrawCallback', 'preDraw', [oSettings] );
		if ( $.inArray( false, aPreDraw ) !== -1 )
		{
			_fnProcessingDisplay( oSettings, false );
			return;
		}
	
		var i, iLen, n;
		var anRows = [];
		var iRowCount = 0;
		var asStripeClasses = oSettings.asStripeClasses;
		var iStripes = asStripeClasses.length;
		var iOpenRows = oSettings.aoOpenRows.length;
		var oLang = oSettings.oLanguage;
		var iInitDisplayStart = oSettings.iInitDisplayStart;
		var bServerSide = _fnDataSource( oSettings ) == 'ssp';
		var aiDisplay = oSettings.aiDisplay;
	
		oSettings.bDrawing = true;
	
		/* Check and see if we have an initial draw position from state saving */
		if ( iInitDisplayStart !== undefined && iInitDisplayStart !== -1 )
		{
			oSettings._iDisplayStart = bServerSide ?
				iInitDisplayStart :
				iInitDisplayStart >= oSettings.fnRecordsDisplay() ?
					0 :
					iInitDisplayStart;
	
			oSettings.iInitDisplayStart = -1;
		}
	
		var iDisplayStart = oSettings._iDisplayStart;
		var iDisplayEnd = oSettings.fnDisplayEnd();
	
		/* Server-side processing draw intercept */
		if ( oSettings.bDeferLoading )
		{
			oSettings.bDeferLoading = false;
			oSettings.iDraw++;
			_fnProcessingDisplay( oSettings, false );
		}
		else if ( !bServerSide )
		{
			oSettings.iDraw++;
		}
		else if ( !oSettings.bDestroying && !_fnAjaxUpdate( oSettings ) )
		{
			return;
		}
	
		if ( aiDisplay.length !== 0 )
		{
			var iStart = bServerSide ? 0 : iDisplayStart;
			var iEnd = bServerSide ? oSettings.aoData.length : iDisplayEnd;
	
			for ( var j=iStart ; j<iEnd ; j++ )
			{
				var iDataIndex = aiDisplay[j];
				var aoData = oSettings.aoData[ iDataIndex ];
				if ( aoData.nTr === null )
				{
					_fnCreateTr( oSettings, iDataIndex );
				}
	
				var nRow = aoData.nTr;
	
				/* Remove the old striping classes and then add the new one */
				if ( iStripes !== 0 )
				{
					var sStripe = asStripeClasses[ iRowCount % iStripes ];
					if ( aoData._sRowStripe != sStripe )
					{
						$(nRow).removeClass( aoData._sRowStripe ).addClass( sStripe );
						aoData._sRowStripe = sStripe;
					}
				}
	
				// Row callback functions - might want to manipulate the row
				// iRowCount and j are not currently documented. Are they at all
				// useful?
				_fnCallbackFire( oSettings, 'aoRowCallback', null,
					[nRow, aoData._aData, iRowCount, j] );
	
				anRows.push( nRow );
				iRowCount++;
			}
		}
		else
		{
			/* Table is empty - create a row with an empty message in it */
			var sZero = oLang.sZeroRecords;
			if ( oSettings.iDraw == 1 &&  _fnDataSource( oSettings ) == 'ajax' )
			{
				sZero = oLang.sLoadingRecords;
			}
			else if ( oLang.sEmptyTable && oSettings.fnRecordsTotal() === 0 )
			{
				sZero = oLang.sEmptyTable;
			}
	
			anRows[ 0 ] = $( '<tr/>', { 'class': iStripes ? asStripeClasses[0] : '' } )
				.append( $('<td />', {
					'valign':  'top',
					'colSpan': _fnVisbleColumns( oSettings ),
					'class':   oSettings.oClasses.sRowEmpty
				} ).html( sZero ) )[0];
		}
	
		/* Header and footer callbacks */
		_fnCallbackFire( oSettings, 'aoHeaderCallback', 'header', [ $(oSettings.nTHead).children('tr')[0],
			_fnGetDataMaster( oSettings ), iDisplayStart, iDisplayEnd, aiDisplay ] );
	
		_fnCallbackFire( oSettings, 'aoFooterCallback', 'footer', [ $(oSettings.nTFoot).children('tr')[0],
			_fnGetDataMaster( oSettings ), iDisplayStart, iDisplayEnd, aiDisplay ] );
	
		var body = $(oSettings.nTBody);
	
		body.children().detach();
		body.append( $(anRows) );
	
		/* Call all required callback functions for the end of a draw */
		_fnCallbackFire( oSettings, 'aoDrawCallback', 'draw', [oSettings] );
	
		/* Draw is complete, sorting and filtering must be as well */
		oSettings.bSorted = false;
		oSettings.bFiltered = false;
		oSettings.bDrawing = false;
	}
	
	
	/**
	 * Redraw the table - taking account of the various features which are enabled
	 *  @param {object} oSettings dataTables settings object
	 *  @param {boolean} [holdPosition] Keep the current paging position. By default
	 *    the paging is reset to the first page
	 *  @memberof DataTable#oApi
	 */
	function _fnReDraw( settings, holdPosition )
	{
		var
			features = settings.oFeatures,
			sort     = features.bSort,
			filter   = features.bFilter;
	
		if ( sort ) {
			_fnSort( settings );
		}
	
		if ( filter ) {
			_fnFilterComplete( settings, settings.oPreviousSearch );
		}
		else {
			// No filtering, so we want to just use the display master
			settings.aiDisplay = settings.aiDisplayMaster.slice();
		}
	
		if ( holdPosition !== true ) {
			settings._iDisplayStart = 0;
		}
	
		// Let any modules know about the draw hold position state (used by
		// scrolling internally)
		settings._drawHold = holdPosition;
	
		_fnDraw( settings );
	
		settings._drawHold = false;
	}
	
	
	/**
	 * Add the options to the page HTML for the table
	 *  @param {object} oSettings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnAddOptionsHtml ( oSettings )
	{
		var classes = oSettings.oClasses;
		var table = $(oSettings.nTable);
		var holding = $('<div/>').insertBefore( table ); // Holding element for speed
		var features = oSettings.oFeatures;
	
		// All DataTables are wrapped in a div
		var insert = $('<div/>', {
			id:      oSettings.sTableId+'_wrapper',
			'class': classes.sWrapper + (oSettings.nTFoot ? '' : ' '+classes.sNoFooter)
		} );
	
		oSettings.nHolding = holding[0];
		oSettings.nTableWrapper = insert[0];
		oSettings.nTableReinsertBefore = oSettings.nTable.nextSibling;
	
		/* Loop over the user set positioning and place the elements as needed */
		var aDom = oSettings.sDom.split('');
		var featureNode, cOption, nNewNode, cNext, sAttr, j;
		for ( var i=0 ; i<aDom.length ; i++ )
		{
			featureNode = null;
			cOption = aDom[i];
	
			if ( cOption == '<' )
			{
				/* New container div */
				nNewNode = $('<div/>')[0];
	
				/* Check to see if we should append an id and/or a class name to the container */
				cNext = aDom[i+1];
				if ( cNext == "'" || cNext == '"' )
				{
					sAttr = "";
					j = 2;
					while ( aDom[i+j] != cNext )
					{
						sAttr += aDom[i+j];
						j++;
					}
	
					/* Replace jQuery UI constants @todo depreciated */
					if ( sAttr == "H" )
					{
						sAttr = classes.sJUIHeader;
					}
					else if ( sAttr == "F" )
					{
						sAttr = classes.sJUIFooter;
					}
	
					/* The attribute can be in the format of "#id.class", "#id" or "class" This logic
					 * breaks the string into parts and applies them as needed
					 */
					if ( sAttr.indexOf('.') != -1 )
					{
						var aSplit = sAttr.split('.');
						nNewNode.id = aSplit[0].substr(1, aSplit[0].length-1);
						nNewNode.className = aSplit[1];
					}
					else if ( sAttr.charAt(0) == "#" )
					{
						nNewNode.id = sAttr.substr(1, sAttr.length-1);
					}
					else
					{
						nNewNode.className = sAttr;
					}
	
					i += j; /* Move along the position array */
				}
	
				insert.append( nNewNode );
				insert = $(nNewNode);
			}
			else if ( cOption == '>' )
			{
				/* End container div */
				insert = insert.parent();
			}
			// @todo Move options into their own plugins?
			else if ( cOption == 'l' && features.bPaginate && features.bLengthChange )
			{
				/* Length */
				featureNode = _fnFeatureHtmlLength( oSettings );
			}
			else if ( cOption == 'f' && features.bFilter )
			{
				/* Filter */
				featureNode = _fnFeatureHtmlFilter( oSettings );
			}
			else if ( cOption == 'r' && features.bProcessing )
			{
				/* pRocessing */
				featureNode = _fnFeatureHtmlProcessing( oSettings );
			}
			else if ( cOption == 't' )
			{
				/* Table */
				featureNode = _fnFeatureHtmlTable( oSettings );
			}
			else if ( cOption ==  'i' && features.bInfo )
			{
				/* Info */
				featureNode = _fnFeatureHtmlInfo( oSettings );
			}
			else if ( cOption == 'p' && features.bPaginate )
			{
				/* Pagination */
				featureNode = _fnFeatureHtmlPaginate( oSettings );
			}
			else if ( DataTable.ext.feature.length !== 0 )
			{
				/* Plug-in features */
				var aoFeatures = DataTable.ext.feature;
				for ( var k=0, kLen=aoFeatures.length ; k<kLen ; k++ )
				{
					if ( cOption == aoFeatures[k].cFeature )
					{
						featureNode = aoFeatures[k].fnInit( oSettings );
						break;
					}
				}
			}
	
			/* Add to the 2D features array */
			if ( featureNode )
			{
				var aanFeatures = oSettings.aanFeatures;
	
				if ( ! aanFeatures[cOption] )
				{
					aanFeatures[cOption] = [];
				}
	
				aanFeatures[cOption].push( featureNode );
				insert.append( featureNode );
			}
		}
	
		/* Built our DOM structure - replace the holding div with what we want */
		holding.replaceWith( insert );
		oSettings.nHolding = null;
	}
	
	
	/**
	 * Use the DOM source to create up an array of header cells. The idea here is to
	 * create a layout grid (array) of rows x columns, which contains a reference
	 * to the cell that that point in the grid (regardless of col/rowspan), such that
	 * any column / row could be removed and the new grid constructed
	 *  @param array {object} aLayout Array to store the calculated layout in
	 *  @param {node} nThead The header/footer element for the table
	 *  @memberof DataTable#oApi
	 */
	function _fnDetectHeader ( aLayout, nThead )
	{
		var nTrs = $(nThead).children('tr');
		var nTr, nCell;
		var i, k, l, iLen, jLen, iColShifted, iColumn, iColspan, iRowspan;
		var bUnique;
		var fnShiftCol = function ( a, i, j ) {
			var k = a[i];
	                while ( k[j] ) {
				j++;
			}
			return j;
		};
	
		aLayout.splice( 0, aLayout.length );
	
		/* We know how many rows there are in the layout - so prep it */
		for ( i=0, iLen=nTrs.length ; i<iLen ; i++ )
		{
			aLayout.push( [] );
		}
	
		/* Calculate a layout array */
		for ( i=0, iLen=nTrs.length ; i<iLen ; i++ )
		{
			nTr = nTrs[i];
			iColumn = 0;
	
			/* For every cell in the row... */
			nCell = nTr.firstChild;
			while ( nCell ) {
				if ( nCell.nodeName.toUpperCase() == "TD" ||
				     nCell.nodeName.toUpperCase() == "TH" )
				{
					/* Get the col and rowspan attributes from the DOM and sanitise them */
					iColspan = nCell.getAttribute('colspan') * 1;
					iRowspan = nCell.getAttribute('rowspan') * 1;
					iColspan = (!iColspan || iColspan===0 || iColspan===1) ? 1 : iColspan;
					iRowspan = (!iRowspan || iRowspan===0 || iRowspan===1) ? 1 : iRowspan;
	
					/* There might be colspan cells already in this row, so shift our target
					 * accordingly
					 */
					iColShifted = fnShiftCol( aLayout, i, iColumn );
	
					/* Cache calculation for unique columns */
					bUnique = iColspan === 1 ? true : false;
	
					/* If there is col / rowspan, copy the information into the layout grid */
					for ( l=0 ; l<iColspan ; l++ )
					{
						for ( k=0 ; k<iRowspan ; k++ )
						{
							aLayout[i+k][iColShifted+l] = {
								"cell": nCell,
								"unique": bUnique
							};
							aLayout[i+k].nTr = nTr;
						}
					}
				}
				nCell = nCell.nextSibling;
			}
		}
	}
	
	
	/**
	 * Get an array of unique th elements, one for each column
	 *  @param {object} oSettings dataTables settings object
	 *  @param {node} nHeader automatically detect the layout from this node - optional
	 *  @param {array} aLayout thead/tfoot layout from _fnDetectHeader - optional
	 *  @returns array {node} aReturn list of unique th's
	 *  @memberof DataTable#oApi
	 */
	function _fnGetUniqueThs ( oSettings, nHeader, aLayout )
	{
		var aReturn = [];
		if ( !aLayout )
		{
			aLayout = oSettings.aoHeader;
			if ( nHeader )
			{
				aLayout = [];
				_fnDetectHeader( aLayout, nHeader );
			}
		}
	
		for ( var i=0, iLen=aLayout.length ; i<iLen ; i++ )
		{
			for ( var j=0, jLen=aLayout[i].length ; j<jLen ; j++ )
			{
				if ( aLayout[i][j].unique &&
					 (!aReturn[j] || !oSettings.bSortCellsTop) )
				{
					aReturn[j] = aLayout[i][j].cell;
				}
			}
		}
	
		return aReturn;
	}
	
	/**
	 * Create an Ajax call based on the table's settings, taking into account that
	 * parameters can have multiple forms, and backwards compatibility.
	 *
	 * @param {object} oSettings dataTables settings object
	 * @param {array} data Data to send to the server, required by
	 *     DataTables - may be augmented by developer callbacks
	 * @param {function} fn Callback function to run when data is obtained
	 */
	function _fnBuildAjax( oSettings, data, fn )
	{
		// Compatibility with 1.9-, allow fnServerData and event to manipulate
		_fnCallbackFire( oSettings, 'aoServerParams', 'serverParams', [data] );
	
		// Convert to object based for 1.10+ if using the old array scheme which can
		// come from server-side processing or serverParams
		if ( data && $.isArray(data) ) {
			var tmp = {};
			var rbracket = /(.*?)\[\]$/;
	
			$.each( data, function (key, val) {
				var match = val.name.match(rbracket);
	
				if ( match ) {
					// Support for arrays
					var name = match[0];
	
					if ( ! tmp[ name ] ) {
						tmp[ name ] = [];
					}
					tmp[ name ].push( val.value );
				}
				else {
					tmp[val.name] = val.value;
				}
			} );
			data = tmp;
		}
	
		var ajaxData;
		var ajax = oSettings.ajax;
		var instance = oSettings.oInstance;
		var callback = function ( json ) {
			_fnCallbackFire( oSettings, null, 'xhr', [oSettings, json, oSettings.jqXHR] );
			fn( json );
		};
	
		if ( $.isPlainObject( ajax ) && ajax.data )
		{
			ajaxData = ajax.data;
	
			var newData = $.isFunction( ajaxData ) ?
				ajaxData( data, oSettings ) :  // fn can manipulate data or return
				ajaxData;                      // an object object or array to merge
	
			// If the function returned something, use that alone
			data = $.isFunction( ajaxData ) && newData ?
				newData :
				$.extend( true, data, newData );
	
			// Remove the data property as we've resolved it already and don't want
			// jQuery to do it again (it is restored at the end of the function)
			delete ajax.data;
		}
	
		var baseAjax = {
			"data": data,
			"success": function (json) {
				var error = json.error || json.sError;
				if ( error ) {
					_fnLog( oSettings, 0, error );
				}
	
				oSettings.json = json;
				callback( json );
			},
			"dataType": "json",
			"cache": false,
			"type": oSettings.sServerMethod,
			"error": function (xhr, error, thrown) {
				var ret = _fnCallbackFire( oSettings, null, 'xhr', [oSettings, null, oSettings.jqXHR] );
	
				if ( $.inArray( true, ret ) === -1 ) {
					if ( error == "parsererror" ) {
						_fnLog( oSettings, 0, 'Invalid JSON response', 1 );
					}
					else if ( xhr.readyState === 4 ) {
						_fnLog( oSettings, 0, 'Ajax error', 7 );
					}
				}
	
				_fnProcessingDisplay( oSettings, false );
			}
		};
	
		// Store the data submitted for the API
		oSettings.oAjaxData = data;
	
		// Allow plug-ins and external processes to modify the data
		_fnCallbackFire( oSettings, null, 'preXhr', [oSettings, data] );
	
		if ( oSettings.fnServerData )
		{
			// DataTables 1.9- compatibility
			oSettings.fnServerData.call( instance,
				oSettings.sAjaxSource,
				$.map( data, function (val, key) { // Need to convert back to 1.9 trad format
					return { name: key, value: val };
				} ),
				callback,
				oSettings
			);
		}
		else if ( oSettings.sAjaxSource || typeof ajax === 'string' )
		{
			// DataTables 1.9- compatibility
			oSettings.jqXHR = $.ajax( $.extend( baseAjax, {
				url: ajax || oSettings.sAjaxSource
			} ) );
		}
		else if ( $.isFunction( ajax ) )
		{
			// Is a function - let the caller define what needs to be done
			oSettings.jqXHR = ajax.call( instance, data, callback, oSettings );
		}
		else
		{
			// Object to extend the base settings
			oSettings.jqXHR = $.ajax( $.extend( baseAjax, ajax ) );
	
			// Restore for next time around
			ajax.data = ajaxData;
		}
	}
	
	
	/**
	 * Update the table using an Ajax call
	 *  @param {object} settings dataTables settings object
	 *  @returns {boolean} Block the table drawing or not
	 *  @memberof DataTable#oApi
	 */
	function _fnAjaxUpdate( settings )
	{
		if ( settings.bAjaxDataGet ) {
			settings.iDraw++;
			_fnProcessingDisplay( settings, true );
	
			_fnBuildAjax(
				settings,
				_fnAjaxParameters( settings ),
				function(json) {
					_fnAjaxUpdateDraw( settings, json );
				}
			);
	
			return false;
		}
		return true;
	}
	
	
	/**
	 * Build up the parameters in an object needed for a server-side processing
	 * request. Note that this is basically done twice, is different ways - a modern
	 * method which is used by default in DataTables 1.10 which uses objects and
	 * arrays, or the 1.9- method with is name / value pairs. 1.9 method is used if
	 * the sAjaxSource option is used in the initialisation, or the legacyAjax
	 * option is set.
	 *  @param {object} oSettings dataTables settings object
	 *  @returns {bool} block the table drawing or not
	 *  @memberof DataTable#oApi
	 */
	function _fnAjaxParameters( settings )
	{
		var
			columns = settings.aoColumns,
			columnCount = columns.length,
			features = settings.oFeatures,
			preSearch = settings.oPreviousSearch,
			preColSearch = settings.aoPreSearchCols,
			i, data = [], dataProp, column, columnSearch,
			sort = _fnSortFlatten( settings ),
			displayStart = settings._iDisplayStart,
			displayLength = features.bPaginate !== false ?
				settings._iDisplayLength :
				-1;
	
		var param = function ( name, value ) {
			data.push( { 'name': name, 'value': value } );
		};
	
		// DataTables 1.9- compatible method
		param( 'sEcho',          settings.iDraw );
		param( 'iColumns',       columnCount );
		param( 'sColumns',       _pluck( columns, 'sName' ).join(',') );
		param( 'iDisplayStart',  displayStart );
		param( 'iDisplayLength', displayLength );
	
		// DataTables 1.10+ method
		var d = {
			draw:    settings.iDraw,
			columns: [],
			order:   [],
			start:   displayStart,
			length:  displayLength,
			search:  {
				value: preSearch.sSearch,
				regex: preSearch.bRegex
			}
		};
	
		for ( i=0 ; i<columnCount ; i++ ) {
			column = columns[i];
			columnSearch = preColSearch[i];
			dataProp = typeof column.mData=="function" ? 'function' : column.mData ;
	
			d.columns.push( {
				data:       dataProp,
				name:       column.sName,
				searchable: column.bSearchable,
				orderable:  column.bSortable,
				search:     {
					value: columnSearch.sSearch,
					regex: columnSearch.bRegex
				}
			} );
	
			param( "mDataProp_"+i, dataProp );
	
			if ( features.bFilter ) {
				param( 'sSearch_'+i,     columnSearch.sSearch );
				param( 'bRegex_'+i,      columnSearch.bRegex );
				param( 'bSearchable_'+i, column.bSearchable );
			}
	
			if ( features.bSort ) {
				param( 'bSortable_'+i, column.bSortable );
			}
		}
	
		if ( features.bFilter ) {
			param( 'sSearch', preSearch.sSearch );
			param( 'bRegex', preSearch.bRegex );
		}
	
		if ( features.bSort ) {
			$.each( sort, function ( i, val ) {
				d.order.push( { column: val.col, dir: val.dir } );
	
				param( 'iSortCol_'+i, val.col );
				param( 'sSortDir_'+i, val.dir );
			} );
	
			param( 'iSortingCols', sort.length );
		}
	
		// If the legacy.ajax parameter is null, then we automatically decide which
		// form to use, based on sAjaxSource
		var legacy = DataTable.ext.legacy.ajax;
		if ( legacy === null ) {
			return settings.sAjaxSource ? data : d;
		}
	
		// Otherwise, if legacy has been specified then we use that to decide on the
		// form
		return legacy ? data : d;
	}
	
	
	/**
	 * Data the data from the server (nuking the old) and redraw the table
	 *  @param {object} oSettings dataTables settings object
	 *  @param {object} json json data return from the server.
	 *  @param {string} json.sEcho Tracking flag for DataTables to match requests
	 *  @param {int} json.iTotalRecords Number of records in the data set, not accounting for filtering
	 *  @param {int} json.iTotalDisplayRecords Number of records in the data set, accounting for filtering
	 *  @param {array} json.aaData The data to display on this page
	 *  @param {string} [json.sColumns] Column ordering (sName, comma separated)
	 *  @memberof DataTable#oApi
	 */
	function _fnAjaxUpdateDraw ( settings, json )
	{
		// v1.10 uses camelCase variables, while 1.9 uses Hungarian notation.
		// Support both
		var compat = function ( old, modern ) {
			return json[old] !== undefined ? json[old] : json[modern];
		};
	
		var data = _fnAjaxDataSrc( settings, json );
		var draw            = compat( 'sEcho',                'draw' );
		var recordsTotal    = compat( 'iTotalRecords',        'recordsTotal' );
		var recordsFiltered = compat( 'iTotalDisplayRecords', 'recordsFiltered' );
	
		if ( draw ) {
			// Protect against out of sequence returns
			if ( draw*1 < settings.iDraw ) {
				return;
			}
			settings.iDraw = draw * 1;
		}
	
		_fnClearTable( settings );
		settings._iRecordsTotal   = parseInt(recordsTotal, 10);
		settings._iRecordsDisplay = parseInt(recordsFiltered, 10);
	
		for ( var i=0, ien=data.length ; i<ien ; i++ ) {
			_fnAddData( settings, data[i] );
		}
		settings.aiDisplay = settings.aiDisplayMaster.slice();
	
		settings.bAjaxDataGet = false;
		_fnDraw( settings );
	
		if ( ! settings._bInitComplete ) {
			_fnInitComplete( settings, json );
		}
	
		settings.bAjaxDataGet = true;
		_fnProcessingDisplay( settings, false );
	}
	
	
	/**
	 * Get the data from the JSON data source to use for drawing a table. Using
	 * `_fnGetObjectDataFn` allows the data to be sourced from a property of the
	 * source object, or from a processing function.
	 *  @param {object} oSettings dataTables settings object
	 *  @param  {object} json Data source object / array from the server
	 *  @return {array} Array of data to use
	 */
	function _fnAjaxDataSrc ( oSettings, json )
	{
		var dataSrc = $.isPlainObject( oSettings.ajax ) && oSettings.ajax.dataSrc !== undefined ?
			oSettings.ajax.dataSrc :
			oSettings.sAjaxDataProp; // Compatibility with 1.9-.
	
		// Compatibility with 1.9-. In order to read from aaData, check if the
		// default has been changed, if not, check for aaData
		if ( dataSrc === 'data' ) {
			return json.aaData || json[dataSrc];
		}
	
		return dataSrc !== "" ?
			_fnGetObjectDataFn( dataSrc )( json ) :
			json;
	}
	
	/**
	 * Generate the node required for filtering text
	 *  @returns {node} Filter control element
	 *  @param {object} oSettings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnFeatureHtmlFilter ( settings )
	{
		var classes = settings.oClasses;
		var tableId = settings.sTableId;
		var language = settings.oLanguage;
		var previousSearch = settings.oPreviousSearch;
		var features = settings.aanFeatures;
		var input = '<input type="search" class="'+classes.sFilterInput+'"/>';
	
		var str = language.sSearch;
		str = str.match(/_INPUT_/) ?
			str.replace('_INPUT_', input) :
			str+input;
	
		var filter = $('<div/>', {
				'id': ! features.f ? tableId+'_filter' : null,
				'class': classes.sFilter
			} )
			.append( $('<label/>' ).append( str ) );
	
		var searchFn = function() {
			/* Update all other filter input elements for the new display */
			var n = features.f;
			var val = !this.value ? "" : this.value; // mental IE8 fix :-(
	
			/* Now do the filter */
			if ( val != previousSearch.sSearch ) {
				_fnFilterComplete( settings, {
					"sSearch": val,
					"bRegex": previousSearch.bRegex,
					"bSmart": previousSearch.bSmart ,
					"bCaseInsensitive": previousSearch.bCaseInsensitive
				} );
	
				// Need to redraw, without resorting
				settings._iDisplayStart = 0;
				_fnDraw( settings );
			}
		};
	
		var searchDelay = settings.searchDelay !== null ?
			settings.searchDelay :
			_fnDataSource( settings ) === 'ssp' ?
				400 :
				0;
	
		var jqFilter = $('input', filter)
			.val( previousSearch.sSearch )
			.attr( 'placeholder', language.sSearchPlaceholder )
			.on(
				'keyup.DT search.DT input.DT paste.DT cut.DT',
				searchDelay ?
					_fnThrottle( searchFn, searchDelay ) :
					searchFn
			)
			.on( 'keypress.DT', function(e) {
				/* Prevent form submission */
				if ( e.keyCode == 13 ) {
					return false;
				}
			} )
			.attr('aria-controls', tableId);
	
		// Update the input elements whenever the table is filtered
		$(settings.nTable).on( 'search.dt.DT', function ( ev, s ) {
			if ( settings === s ) {
				// IE9 throws an 'unknown error' if document.activeElement is used
				// inside an iframe or frame...
				try {
					if ( jqFilter[0] !== document.activeElement ) {
						jqFilter.val( previousSearch.sSearch );
					}
				}
				catch ( e ) {}
			}
		} );
	
		return filter[0];
	}
	
	
	/**
	 * Filter the table using both the global filter and column based filtering
	 *  @param {object} oSettings dataTables settings object
	 *  @param {object} oSearch search information
	 *  @param {int} [iForce] force a research of the master array (1) or not (undefined or 0)
	 *  @memberof DataTable#oApi
	 */
	function _fnFilterComplete ( oSettings, oInput, iForce )
	{
		var oPrevSearch = oSettings.oPreviousSearch;
		var aoPrevSearch = oSettings.aoPreSearchCols;
		var fnSaveFilter = function ( oFilter ) {
			/* Save the filtering values */
			oPrevSearch.sSearch = oFilter.sSearch;
			oPrevSearch.bRegex = oFilter.bRegex;
			oPrevSearch.bSmart = oFilter.bSmart;
			oPrevSearch.bCaseInsensitive = oFilter.bCaseInsensitive;
		};
		var fnRegex = function ( o ) {
			// Backwards compatibility with the bEscapeRegex option
			return o.bEscapeRegex !== undefined ? !o.bEscapeRegex : o.bRegex;
		};
	
		// Resolve any column types that are unknown due to addition or invalidation
		// @todo As per sort - can this be moved into an event handler?
		_fnColumnTypes( oSettings );
	
		/* In server-side processing all filtering is done by the server, so no point hanging around here */
		if ( _fnDataSource( oSettings ) != 'ssp' )
		{
			/* Global filter */
			_fnFilter( oSettings, oInput.sSearch, iForce, fnRegex(oInput), oInput.bSmart, oInput.bCaseInsensitive );
			fnSaveFilter( oInput );
	
			/* Now do the individual column filter */
			for ( var i=0 ; i<aoPrevSearch.length ; i++ )
			{
				_fnFilterColumn( oSettings, aoPrevSearch[i].sSearch, i, fnRegex(aoPrevSearch[i]),
					aoPrevSearch[i].bSmart, aoPrevSearch[i].bCaseInsensitive );
			}
	
			/* Custom filtering */
			_fnFilterCustom( oSettings );
		}
		else
		{
			fnSaveFilter( oInput );
		}
	
		/* Tell the draw function we have been filtering */
		oSettings.bFiltered = true;
		_fnCallbackFire( oSettings, null, 'search', [oSettings] );
	}
	
	
	/**
	 * Apply custom filtering functions
	 *  @param {object} oSettings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnFilterCustom( settings )
	{
		var filters = DataTable.ext.search;
		var displayRows = settings.aiDisplay;
		var row, rowIdx;
	
		for ( var i=0, ien=filters.length ; i<ien ; i++ ) {
			var rows = [];
	
			// Loop over each row and see if it should be included
			for ( var j=0, jen=displayRows.length ; j<jen ; j++ ) {
				rowIdx = displayRows[ j ];
				row = settings.aoData[ rowIdx ];
	
				if ( filters[i]( settings, row._aFilterData, rowIdx, row._aData, j ) ) {
					rows.push( rowIdx );
				}
			}
	
			// So the array reference doesn't break set the results into the
			// existing array
			displayRows.length = 0;
			$.merge( displayRows, rows );
		}
	}
	
	
	/**
	 * Filter the table on a per-column basis
	 *  @param {object} oSettings dataTables settings object
	 *  @param {string} sInput string to filter on
	 *  @param {int} iColumn column to filter
	 *  @param {bool} bRegex treat search string as a regular expression or not
	 *  @param {bool} bSmart use smart filtering or not
	 *  @param {bool} bCaseInsensitive Do case insenstive matching or not
	 *  @memberof DataTable#oApi
	 */
	function _fnFilterColumn ( settings, searchStr, colIdx, regex, smart, caseInsensitive )
	{
		if ( searchStr === '' ) {
			return;
		}
	
		var data;
		var out = [];
		var display = settings.aiDisplay;
		var rpSearch = _fnFilterCreateSearch( searchStr, regex, smart, caseInsensitive );
	
		for ( var i=0 ; i<display.length ; i++ ) {
			data = settings.aoData[ display[i] ]._aFilterData[ colIdx ];
	
			if ( rpSearch.test( data ) ) {
				out.push( display[i] );
			}
		}
	
		settings.aiDisplay = out;
	}
	
	
	/**
	 * Filter the data table based on user input and draw the table
	 *  @param {object} settings dataTables settings object
	 *  @param {string} input string to filter on
	 *  @param {int} force optional - force a research of the master array (1) or not (undefined or 0)
	 *  @param {bool} regex treat as a regular expression or not
	 *  @param {bool} smart perform smart filtering or not
	 *  @param {bool} caseInsensitive Do case insenstive matching or not
	 *  @memberof DataTable#oApi
	 */
	function _fnFilter( settings, input, force, regex, smart, caseInsensitive )
	{
		var rpSearch = _fnFilterCreateSearch( input, regex, smart, caseInsensitive );
		var prevSearch = settings.oPreviousSearch.sSearch;
		var displayMaster = settings.aiDisplayMaster;
		var display, invalidated, i;
		var filtered = [];
	
		// Need to take account of custom filtering functions - always filter
		if ( DataTable.ext.search.length !== 0 ) {
			force = true;
		}
	
		// Check if any of the rows were invalidated
		invalidated = _fnFilterData( settings );
	
		// If the input is blank - we just want the full data set
		if ( input.length <= 0 ) {
			settings.aiDisplay = displayMaster.slice();
		}
		else {
			// New search - start from the master array
			if ( invalidated ||
				 force ||
				 prevSearch.length > input.length ||
				 input.indexOf(prevSearch) !== 0 ||
				 settings.bSorted // On resort, the display master needs to be
				                  // re-filtered since indexes will have changed
			) {
				settings.aiDisplay = displayMaster.slice();
			}
	
			// Search the display array
			display = settings.aiDisplay;
	
			for ( i=0 ; i<display.length ; i++ ) {
				if ( rpSearch.test( settings.aoData[ display[i] ]._sFilterRow ) ) {
					filtered.push( display[i] );
				}
			}
	
			settings.aiDisplay = filtered;
		}
	}
	
	
	/**
	 * Build a regular expression object suitable for searching a table
	 *  @param {string} sSearch string to search for
	 *  @param {bool} bRegex treat as a regular expression or not
	 *  @param {bool} bSmart perform smart filtering or not
	 *  @param {bool} bCaseInsensitive Do case insensitive matching or not
	 *  @returns {RegExp} constructed object
	 *  @memberof DataTable#oApi
	 */
	function _fnFilterCreateSearch( search, regex, smart, caseInsensitive )
	{
		search = regex ?
			search :
			_fnEscapeRegex( search );
		
		if ( smart ) {
			/* For smart filtering we want to allow the search to work regardless of
			 * word order. We also want double quoted text to be preserved, so word
			 * order is important - a la google. So this is what we want to
			 * generate:
			 * 
			 * ^(?=.*?\bone\b)(?=.*?\btwo three\b)(?=.*?\bfour\b).*$
			 */
			var a = $.map( search.match( /"[^"]+"|[^ ]+/g ) || [''], function ( word ) {
				if ( word.charAt(0) === '"' ) {
					var m = word.match( /^"(.*)"$/ );
					word = m ? m[1] : word;
				}
	
				return word.replace('"', '');
			} );
	
			search = '^(?=.*?'+a.join( ')(?=.*?' )+').*$';
		}
	
		return new RegExp( search, caseInsensitive ? 'i' : '' );
	}
	
	
	/**
	 * Escape a string such that it can be used in a regular expression
	 *  @param {string} sVal string to escape
	 *  @returns {string} escaped string
	 *  @memberof DataTable#oApi
	 */
	var _fnEscapeRegex = DataTable.util.escapeRegex;
	
	var __filter_div = $('<div>')[0];
	var __filter_div_textContent = __filter_div.textContent !== undefined;
	
	// Update the filtering data for each row if needed (by invalidation or first run)
	function _fnFilterData ( settings )
	{
		var columns = settings.aoColumns;
		var column;
		var i, j, ien, jen, filterData, cellData, row;
		var fomatters = DataTable.ext.type.search;
		var wasInvalidated = false;
	
		for ( i=0, ien=settings.aoData.length ; i<ien ; i++ ) {
			row = settings.aoData[i];
	
			if ( ! row._aFilterData ) {
				filterData = [];
	
				for ( j=0, jen=columns.length ; j<jen ; j++ ) {
					column = columns[j];
	
					if ( column.bSearchable ) {
						cellData = _fnGetCellData( settings, i, j, 'filter' );
	
						if ( fomatters[ column.sType ] ) {
							cellData = fomatters[ column.sType ]( cellData );
						}
	
						// Search in DataTables 1.10 is string based. In 1.11 this
						// should be altered to also allow strict type checking.
						if ( cellData === null ) {
							cellData = '';
						}
	
						if ( typeof cellData !== 'string' && cellData.toString ) {
							cellData = cellData.toString();
						}
					}
					else {
						cellData = '';
					}
	
					// If it looks like there is an HTML entity in the string,
					// attempt to decode it so sorting works as expected. Note that
					// we could use a single line of jQuery to do this, but the DOM
					// method used here is much faster http://jsperf.com/html-decode
					if ( cellData.indexOf && cellData.indexOf('&') !== -1 ) {
						__filter_div.innerHTML = cellData;
						cellData = __filter_div_textContent ?
							__filter_div.textContent :
							__filter_div.innerText;
					}
	
					if ( cellData.replace ) {
						cellData = cellData.replace(/[\r\n]/g, '');
					}
	
					filterData.push( cellData );
				}
	
				row._aFilterData = filterData;
				row._sFilterRow = filterData.join('  ');
				wasInvalidated = true;
			}
		}
	
		return wasInvalidated;
	}
	
	
	/**
	 * Convert from the internal Hungarian notation to camelCase for external
	 * interaction
	 *  @param {object} obj Object to convert
	 *  @returns {object} Inverted object
	 *  @memberof DataTable#oApi
	 */
	function _fnSearchToCamel ( obj )
	{
		return {
			search:          obj.sSearch,
			smart:           obj.bSmart,
			regex:           obj.bRegex,
			caseInsensitive: obj.bCaseInsensitive
		};
	}
	
	
	
	/**
	 * Convert from camelCase notation to the internal Hungarian. We could use the
	 * Hungarian convert function here, but this is cleaner
	 *  @param {object} obj Object to convert
	 *  @returns {object} Inverted object
	 *  @memberof DataTable#oApi
	 */
	function _fnSearchToHung ( obj )
	{
		return {
			sSearch:          obj.search,
			bSmart:           obj.smart,
			bRegex:           obj.regex,
			bCaseInsensitive: obj.caseInsensitive
		};
	}
	
	/**
	 * Generate the node required for the info display
	 *  @param {object} oSettings dataTables settings object
	 *  @returns {node} Information element
	 *  @memberof DataTable#oApi
	 */
	function _fnFeatureHtmlInfo ( settings )
	{
		var
			tid = settings.sTableId,
			nodes = settings.aanFeatures.i,
			n = $('<div/>', {
				'class': settings.oClasses.sInfo,
				'id': ! nodes ? tid+'_info' : null
			} );
	
		if ( ! nodes ) {
			// Update display on each draw
			settings.aoDrawCallback.push( {
				"fn": _fnUpdateInfo,
				"sName": "information"
			} );
	
			n
				.attr( 'role', 'status' )
				.attr( 'aria-live', 'polite' );
	
			// Table is described by our info div
			$(settings.nTable).attr( 'aria-describedby', tid+'_info' );
		}
	
		return n[0];
	}
	
	
	/**
	 * Update the information elements in the display
	 *  @param {object} settings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnUpdateInfo ( settings )
	{
		/* Show information about the table */
		var nodes = settings.aanFeatures.i;
		if ( nodes.length === 0 ) {
			return;
		}
	
		var
			lang  = settings.oLanguage,
			start = settings._iDisplayStart+1,
			end   = settings.fnDisplayEnd(),
			max   = settings.fnRecordsTotal(),
			total = settings.fnRecordsDisplay(),
			out   = total ?
				lang.sInfo :
				lang.sInfoEmpty;
	
		if ( total !== max ) {
			/* Record set after filtering */
			out += ' ' + lang.sInfoFiltered;
		}
	
		// Convert the macros
		out += lang.sInfoPostFix;
		out = _fnInfoMacros( settings, out );
	
		var callback = lang.fnInfoCallback;
		if ( callback !== null ) {
			out = callback.call( settings.oInstance,
				settings, start, end, max, total, out
			);
		}
	
		$(nodes).html( out );
	}
	
	
	function _fnInfoMacros ( settings, str )
	{
		// When infinite scrolling, we are always starting at 1. _iDisplayStart is used only
		// internally
		var
			formatter  = settings.fnFormatNumber,
			start      = settings._iDisplayStart+1,
			len        = settings._iDisplayLength,
			vis        = settings.fnRecordsDisplay(),
			all        = len === -1;
	
		return str.
			replace(/_START_/g, formatter.call( settings, start ) ).
			replace(/_END_/g,   formatter.call( settings, settings.fnDisplayEnd() ) ).
			replace(/_MAX_/g,   formatter.call( settings, settings.fnRecordsTotal() ) ).
			replace(/_TOTAL_/g, formatter.call( settings, vis ) ).
			replace(/_PAGE_/g,  formatter.call( settings, all ? 1 : Math.ceil( start / len ) ) ).
			replace(/_PAGES_/g, formatter.call( settings, all ? 1 : Math.ceil( vis / len ) ) );
	}
	
	
	
	/**
	 * Draw the table for the first time, adding all required features
	 *  @param {object} settings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnInitialise ( settings )
	{
		var i, iLen, iAjaxStart=settings.iInitDisplayStart;
		var columns = settings.aoColumns, column;
		var features = settings.oFeatures;
		var deferLoading = settings.bDeferLoading; // value modified by the draw
	
		/* Ensure that the table data is fully initialised */
		if ( ! settings.bInitialised ) {
			setTimeout( function(){ _fnInitialise( settings ); }, 200 );
			return;
		}
	
		/* Show the display HTML options */
		_fnAddOptionsHtml( settings );
	
		/* Build and draw the header / footer for the table */
		_fnBuildHead( settings );
		_fnDrawHead( settings, settings.aoHeader );
		_fnDrawHead( settings, settings.aoFooter );
	
		/* Okay to show that something is going on now */
		_fnProcessingDisplay( settings, true );
	
		/* Calculate sizes for columns */
		if ( features.bAutoWidth ) {
			_fnCalculateColumnWidths( settings );
		}
	
		for ( i=0, iLen=columns.length ; i<iLen ; i++ ) {
			column = columns[i];
	
			if ( column.sWidth ) {
				column.nTh.style.width = _fnStringToCss( column.sWidth );
			}
		}
	
		_fnCallbackFire( settings, null, 'preInit', [settings] );
	
		// If there is default sorting required - let's do it. The sort function
		// will do the drawing for us. Otherwise we draw the table regardless of the
		// Ajax source - this allows the table to look initialised for Ajax sourcing
		// data (show 'loading' message possibly)
		_fnReDraw( settings );
	
		// Server-side processing init complete is done by _fnAjaxUpdateDraw
		var dataSrc = _fnDataSource( settings );
		if ( dataSrc != 'ssp' || deferLoading ) {
			// if there is an ajax source load the data
			if ( dataSrc == 'ajax' ) {
				_fnBuildAjax( settings, [], function(json) {
					var aData = _fnAjaxDataSrc( settings, json );
	
					// Got the data - add it to the table
					for ( i=0 ; i<aData.length ; i++ ) {
						_fnAddData( settings, aData[i] );
					}
	
					// Reset the init display for cookie saving. We've already done
					// a filter, and therefore cleared it before. So we need to make
					// it appear 'fresh'
					settings.iInitDisplayStart = iAjaxStart;
	
					_fnReDraw( settings );
	
					_fnProcessingDisplay( settings, false );
					_fnInitComplete( settings, json );
				}, settings );
			}
			else {
				_fnProcessingDisplay( settings, false );
				_fnInitComplete( settings );
			}
		}
	}
	
	
	/**
	 * Draw the table for the first time, adding all required features
	 *  @param {object} oSettings dataTables settings object
	 *  @param {object} [json] JSON from the server that completed the table, if using Ajax source
	 *    with client-side processing (optional)
	 *  @memberof DataTable#oApi
	 */
	function _fnInitComplete ( settings, json )
	{
		settings._bInitComplete = true;
	
		// When data was added after the initialisation (data or Ajax) we need to
		// calculate the column sizing
		if ( json || settings.oInit.aaData ) {
			_fnAdjustColumnSizing( settings );
		}
	
		_fnCallbackFire( settings, null, 'plugin-init', [settings, json] );
		_fnCallbackFire( settings, 'aoInitComplete', 'init', [settings, json] );
	}
	
	
	function _fnLengthChange ( settings, val )
	{
		var len = parseInt( val, 10 );
		settings._iDisplayLength = len;
	
		_fnLengthOverflow( settings );
	
		// Fire length change event
		_fnCallbackFire( settings, null, 'length', [settings, len] );
	}
	
	
	/**
	 * Generate the node required for user display length changing
	 *  @param {object} settings dataTables settings object
	 *  @returns {node} Display length feature node
	 *  @memberof DataTable#oApi
	 */
	function _fnFeatureHtmlLength ( settings )
	{
		var
			classes  = settings.oClasses,
			tableId  = settings.sTableId,
			menu     = settings.aLengthMenu,
			d2       = $.isArray( menu[0] ),
			lengths  = d2 ? menu[0] : menu,
			language = d2 ? menu[1] : menu;
	
		var select = $('<select/>', {
			'name':          tableId+'_length',
			'aria-controls': tableId,
			'class':         classes.sLengthSelect
		} );
	
		for ( var i=0, ien=lengths.length ; i<ien ; i++ ) {
			select[0][ i ] = new Option(
				typeof language[i] === 'number' ?
					settings.fnFormatNumber( language[i] ) :
					language[i],
				lengths[i]
			);
		}
	
		var div = $('<div><label/></div>').addClass( classes.sLength );
		if ( ! settings.aanFeatures.l ) {
			div[0].id = tableId+'_length';
		}
	
		div.children().append(
			settings.oLanguage.sLengthMenu.replace( '_MENU_', select[0].outerHTML )
		);
	
		// Can't use `select` variable as user might provide their own and the
		// reference is broken by the use of outerHTML
		$('select', div)
			.val( settings._iDisplayLength )
			.on( 'change.DT', function(e) {
				_fnLengthChange( settings, $(this).val() );
				_fnDraw( settings );
			} );
	
		// Update node value whenever anything changes the table's length
		$(settings.nTable).on( 'length.dt.DT', function (e, s, len) {
			if ( settings === s ) {
				$('select', div).val( len );
			}
		} );
	
		return div[0];
	}
	
	
	
	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Note that most of the paging logic is done in
	 * DataTable.ext.pager
	 */
	
	/**
	 * Generate the node required for default pagination
	 *  @param {object} oSettings dataTables settings object
	 *  @returns {node} Pagination feature node
	 *  @memberof DataTable#oApi
	 */
	function _fnFeatureHtmlPaginate ( settings )
	{
		var
			type   = settings.sPaginationType,
			plugin = DataTable.ext.pager[ type ],
			modern = typeof plugin === 'function',
			redraw = function( settings ) {
				_fnDraw( settings );
			},
			node = $('<div/>').addClass( settings.oClasses.sPaging + type )[0],
			features = settings.aanFeatures;
	
		if ( ! modern ) {
			plugin.fnInit( settings, node, redraw );
		}
	
		/* Add a draw callback for the pagination on first instance, to update the paging display */
		if ( ! features.p )
		{
			node.id = settings.sTableId+'_paginate';
	
			settings.aoDrawCallback.push( {
				"fn": function( settings ) {
					if ( modern ) {
						var
							start      = settings._iDisplayStart,
							len        = settings._iDisplayLength,
							visRecords = settings.fnRecordsDisplay(),
							all        = len === -1,
							page = all ? 0 : Math.ceil( start / len ),
							pages = all ? 1 : Math.ceil( visRecords / len ),
							buttons = plugin(page, pages),
							i, ien;
	
						for ( i=0, ien=features.p.length ; i<ien ; i++ ) {
							_fnRenderer( settings, 'pageButton' )(
								settings, features.p[i], i, buttons, page, pages
							);
						}
					}
					else {
						plugin.fnUpdate( settings, redraw );
					}
				},
				"sName": "pagination"
			} );
		}
	
		return node;
	}
	
	
	/**
	 * Alter the display settings to change the page
	 *  @param {object} settings DataTables settings object
	 *  @param {string|int} action Paging action to take: "first", "previous",
	 *    "next" or "last" or page number to jump to (integer)
	 *  @param [bool] redraw Automatically draw the update or not
	 *  @returns {bool} true page has changed, false - no change
	 *  @memberof DataTable#oApi
	 */
	function _fnPageChange ( settings, action, redraw )
	{
		var
			start     = settings._iDisplayStart,
			len       = settings._iDisplayLength,
			records   = settings.fnRecordsDisplay();
	
		if ( records === 0 || len === -1 )
		{
			start = 0;
		}
		else if ( typeof action === "number" )
		{
			start = action * len;
	
			if ( start > records )
			{
				start = 0;
			}
		}
		else if ( action == "first" )
		{
			start = 0;
		}
		else if ( action == "previous" )
		{
			start = len >= 0 ?
				start - len :
				0;
	
			if ( start < 0 )
			{
			  start = 0;
			}
		}
		else if ( action == "next" )
		{
			if ( start + len < records )
			{
				start += len;
			}
		}
		else if ( action == "last" )
		{
			start = Math.floor( (records-1) / len) * len;
		}
		else
		{
			_fnLog( settings, 0, "Unknown paging action: "+action, 5 );
		}
	
		var changed = settings._iDisplayStart !== start;
		settings._iDisplayStart = start;
	
		if ( changed ) {
			_fnCallbackFire( settings, null, 'page', [settings] );
	
			if ( redraw ) {
				_fnDraw( settings );
			}
		}
	
		return changed;
	}
	
	
	
	/**
	 * Generate the node required for the processing node
	 *  @param {object} settings dataTables settings object
	 *  @returns {node} Processing element
	 *  @memberof DataTable#oApi
	 */
	function _fnFeatureHtmlProcessing ( settings )
	{
		return $('<div/>', {
				'id': ! settings.aanFeatures.r ? settings.sTableId+'_processing' : null,
				'class': settings.oClasses.sProcessing
			} )
			.html( settings.oLanguage.sProcessing )
			.insertBefore( settings.nTable )[0];
	}
	
	
	/**
	 * Display or hide the processing indicator
	 *  @param {object} settings dataTables settings object
	 *  @param {bool} show Show the processing indicator (true) or not (false)
	 *  @memberof DataTable#oApi
	 */
	function _fnProcessingDisplay ( settings, show )
	{
		if ( settings.oFeatures.bProcessing ) {
			$(settings.aanFeatures.r).css( 'display', show ? 'block' : 'none' );
		}
	
		_fnCallbackFire( settings, null, 'processing', [settings, show] );
	}
	
	/**
	 * Add any control elements for the table - specifically scrolling
	 *  @param {object} settings dataTables settings object
	 *  @returns {node} Node to add to the DOM
	 *  @memberof DataTable#oApi
	 */
	function _fnFeatureHtmlTable ( settings )
	{
		var table = $(settings.nTable);
	
		// Add the ARIA grid role to the table
		table.attr( 'role', 'grid' );
	
		// Scrolling from here on in
		var scroll = settings.oScroll;
	
		if ( scroll.sX === '' && scroll.sY === '' ) {
			return settings.nTable;
		}
	
		var scrollX = scroll.sX;
		var scrollY = scroll.sY;
		var classes = settings.oClasses;
		var caption = table.children('caption');
		var captionSide = caption.length ? caption[0]._captionSide : null;
		var headerClone = $( table[0].cloneNode(false) );
		var footerClone = $( table[0].cloneNode(false) );
		var footer = table.children('tfoot');
		var _div = '<div/>';
		var size = function ( s ) {
			return !s ? null : _fnStringToCss( s );
		};
	
		if ( ! footer.length ) {
			footer = null;
		}
	
		/*
		 * The HTML structure that we want to generate in this function is:
		 *  div - scroller
		 *    div - scroll head
		 *      div - scroll head inner
		 *        table - scroll head table
		 *          thead - thead
		 *    div - scroll body
		 *      table - table (master table)
		 *        thead - thead clone for sizing
		 *        tbody - tbody
		 *    div - scroll foot
		 *      div - scroll foot inner
		 *        table - scroll foot table
		 *          tfoot - tfoot
		 */
		var scroller = $( _div, { 'class': classes.sScrollWrapper } )
			.append(
				$(_div, { 'class': classes.sScrollHead } )
					.css( {
						overflow: 'hidden',
						position: 'relative',
						border: 0,
						width: scrollX ? size(scrollX) : '100%'
					} )
					.append(
						$(_div, { 'class': classes.sScrollHeadInner } )
							.css( {
								'box-sizing': 'content-box',
								width: scroll.sXInner || '100%'
							} )
							.append(
								headerClone
									.removeAttr('id')
									.css( 'margin-left', 0 )
									.append( captionSide === 'top' ? caption : null )
									.append(
										table.children('thead')
									)
							)
					)
			)
			.append(
				$(_div, { 'class': classes.sScrollBody } )
					.css( {
						position: 'relative',
						overflow: 'auto',
						width: size( scrollX )
					} )
					.append( table )
			);
	
		if ( footer ) {
			scroller.append(
				$(_div, { 'class': classes.sScrollFoot } )
					.css( {
						overflow: 'hidden',
						border: 0,
						width: scrollX ? size(scrollX) : '100%'
					} )
					.append(
						$(_div, { 'class': classes.sScrollFootInner } )
							.append(
								footerClone
									.removeAttr('id')
									.css( 'margin-left', 0 )
									.append( captionSide === 'bottom' ? caption : null )
									.append(
										table.children('tfoot')
									)
							)
					)
			);
		}
	
		var children = scroller.children();
		var scrollHead = children[0];
		var scrollBody = children[1];
		var scrollFoot = footer ? children[2] : null;
	
		// When the body is scrolled, then we also want to scroll the headers
		if ( scrollX ) {
			$(scrollBody).on( 'scroll.DT', function (e) {
				var scrollLeft = this.scrollLeft;
	
				scrollHead.scrollLeft = scrollLeft;
	
				if ( footer ) {
					scrollFoot.scrollLeft = scrollLeft;
				}
			} );
		}
	
		$(scrollBody).css(
			scrollY && scroll.bCollapse ? 'max-height' : 'height', 
			scrollY
		);
	
		settings.nScrollHead = scrollHead;
		settings.nScrollBody = scrollBody;
		settings.nScrollFoot = scrollFoot;
	
		// On redraw - align columns
		settings.aoDrawCallback.push( {
			"fn": _fnScrollDraw,
			"sName": "scrolling"
		} );
	
		return scroller[0];
	}
	
	
	
	/**
	 * Update the header, footer and body tables for resizing - i.e. column
	 * alignment.
	 *
	 * Welcome to the most horrible function DataTables. The process that this
	 * function follows is basically:
	 *   1. Re-create the table inside the scrolling div
	 *   2. Take live measurements from the DOM
	 *   3. Apply the measurements to align the columns
	 *   4. Clean up
	 *
	 *  @param {object} settings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnScrollDraw ( settings )
	{
		// Given that this is such a monster function, a lot of variables are use
		// to try and keep the minimised size as small as possible
		var
			scroll         = settings.oScroll,
			scrollX        = scroll.sX,
			scrollXInner   = scroll.sXInner,
			scrollY        = scroll.sY,
			barWidth       = scroll.iBarWidth,
			divHeader      = $(settings.nScrollHead),
			divHeaderStyle = divHeader[0].style,
			divHeaderInner = divHeader.children('div'),
			divHeaderInnerStyle = divHeaderInner[0].style,
			divHeaderTable = divHeaderInner.children('table'),
			divBodyEl      = settings.nScrollBody,
			divBody        = $(divBodyEl),
			divBodyStyle   = divBodyEl.style,
			divFooter      = $(settings.nScrollFoot),
			divFooterInner = divFooter.children('div'),
			divFooterTable = divFooterInner.children('table'),
			header         = $(settings.nTHead),
			table          = $(settings.nTable),
			tableEl        = table[0],
			tableStyle     = tableEl.style,
			footer         = settings.nTFoot ? $(settings.nTFoot) : null,
			browser        = settings.oBrowser,
			ie67           = browser.bScrollOversize,
			dtHeaderCells  = _pluck( settings.aoColumns, 'nTh' ),
			headerTrgEls, footerTrgEls,
			headerSrcEls, footerSrcEls,
			headerCopy, footerCopy,
			headerWidths=[], footerWidths=[],
			headerContent=[], footerContent=[],
			idx, correction, sanityWidth,
			zeroOut = function(nSizer) {
				var style = nSizer.style;
				style.paddingTop = "0";
				style.paddingBottom = "0";
				style.borderTopWidth = "0";
				style.borderBottomWidth = "0";
				style.height = 0;
			};
	
		// If the scrollbar visibility has changed from the last draw, we need to
		// adjust the column sizes as the table width will have changed to account
		// for the scrollbar
		var scrollBarVis = divBodyEl.scrollHeight > divBodyEl.clientHeight;
		
		if ( settings.scrollBarVis !== scrollBarVis && settings.scrollBarVis !== undefined ) {
			settings.scrollBarVis = scrollBarVis;
			_fnAdjustColumnSizing( settings );
			return; // adjust column sizing will call this function again
		}
		else {
			settings.scrollBarVis = scrollBarVis;
		}
	
		/*
		 * 1. Re-create the table inside the scrolling div
		 */
	
		// Remove the old minimised thead and tfoot elements in the inner table
		table.children('thead, tfoot').remove();
	
		if ( footer ) {
			footerCopy = footer.clone().prependTo( table );
			footerTrgEls = footer.find('tr'); // the original tfoot is in its own table and must be sized
			footerSrcEls = footerCopy.find('tr');
		}
	
		// Clone the current header and footer elements and then place it into the inner table
		headerCopy = header.clone().prependTo( table );
		headerTrgEls = header.find('tr'); // original header is in its own table
		headerSrcEls = headerCopy.find('tr');
		headerCopy.find('th, td').removeAttr('tabindex');
	
	
		/*
		 * 2. Take live measurements from the DOM - do not alter the DOM itself!
		 */
	
		// Remove old sizing and apply the calculated column widths
		// Get the unique column headers in the newly created (cloned) header. We want to apply the
		// calculated sizes to this header
		if ( ! scrollX )
		{
			divBodyStyle.width = '100%';
			divHeader[0].style.width = '100%';
		}
	
		$.each( _fnGetUniqueThs( settings, headerCopy ), function ( i, el ) {
			idx = _fnVisibleToColumnIndex( settings, i );
			el.style.width = settings.aoColumns[idx].sWidth;
		} );
	
		if ( footer ) {
			_fnApplyToChildren( function(n) {
				n.style.width = "";
			}, footerSrcEls );
		}
	
		// Size the table as a whole
		sanityWidth = table.outerWidth();
		if ( scrollX === "" ) {
			// No x scrolling
			tableStyle.width = "100%";
	
			// IE7 will make the width of the table when 100% include the scrollbar
			// - which is shouldn't. When there is a scrollbar we need to take this
			// into account.
			if ( ie67 && (table.find('tbody').height() > divBodyEl.offsetHeight ||
				divBody.css('overflow-y') == "scroll")
			) {
				tableStyle.width = _fnStringToCss( table.outerWidth() - barWidth);
			}
	
			// Recalculate the sanity width
			sanityWidth = table.outerWidth();
		}
		else if ( scrollXInner !== "" ) {
			// legacy x scroll inner has been given - use it
			tableStyle.width = _fnStringToCss(scrollXInner);
	
			// Recalculate the sanity width
			sanityWidth = table.outerWidth();
		}
	
		// Hidden header should have zero height, so remove padding and borders. Then
		// set the width based on the real headers
	
		// Apply all styles in one pass
		_fnApplyToChildren( zeroOut, headerSrcEls );
	
		// Read all widths in next pass
		_fnApplyToChildren( function(nSizer) {
			headerContent.push( nSizer.innerHTML );
			headerWidths.push( _fnStringToCss( $(nSizer).css('width') ) );
		}, headerSrcEls );
	
		// Apply all widths in final pass
		_fnApplyToChildren( function(nToSize, i) {
			// Only apply widths to the DataTables detected header cells - this
			// prevents complex headers from having contradictory sizes applied
			if ( $.inArray( nToSize, dtHeaderCells ) !== -1 ) {
				nToSize.style.width = headerWidths[i];
			}
		}, headerTrgEls );
	
		$(headerSrcEls).height(0);
	
		/* Same again with the footer if we have one */
		if ( footer )
		{
			_fnApplyToChildren( zeroOut, footerSrcEls );
	
			_fnApplyToChildren( function(nSizer) {
				footerContent.push( nSizer.innerHTML );
				footerWidths.push( _fnStringToCss( $(nSizer).css('width') ) );
			}, footerSrcEls );
	
			_fnApplyToChildren( function(nToSize, i) {
				nToSize.style.width = footerWidths[i];
			}, footerTrgEls );
	
			$(footerSrcEls).height(0);
		}
	
	
		/*
		 * 3. Apply the measurements
		 */
	
		// "Hide" the header and footer that we used for the sizing. We need to keep
		// the content of the cell so that the width applied to the header and body
		// both match, but we want to hide it completely. We want to also fix their
		// width to what they currently are
		_fnApplyToChildren( function(nSizer, i) {
			nSizer.innerHTML = '<div class="dataTables_sizing" style="height:0;overflow:hidden;">'+headerContent[i]+'</div>';
			nSizer.style.width = headerWidths[i];
		}, headerSrcEls );
	
		if ( footer )
		{
			_fnApplyToChildren( function(nSizer, i) {
				nSizer.innerHTML = '<div class="dataTables_sizing" style="height:0;overflow:hidden;">'+footerContent[i]+'</div>';
				nSizer.style.width = footerWidths[i];
			}, footerSrcEls );
		}
	
		// Sanity check that the table is of a sensible width. If not then we are going to get
		// misalignment - try to prevent this by not allowing the table to shrink below its min width
		if ( table.outerWidth() < sanityWidth )
		{
			// The min width depends upon if we have a vertical scrollbar visible or not */
			correction = ((divBodyEl.scrollHeight > divBodyEl.offsetHeight ||
				divBody.css('overflow-y') == "scroll")) ?
					sanityWidth+barWidth :
					sanityWidth;
	
			// IE6/7 are a law unto themselves...
			if ( ie67 && (divBodyEl.scrollHeight >
				divBodyEl.offsetHeight || divBody.css('overflow-y') == "scroll")
			) {
				tableStyle.width = _fnStringToCss( correction-barWidth );
			}
	
			// And give the user a warning that we've stopped the table getting too small
			if ( scrollX === "" || scrollXInner !== "" ) {
				_fnLog( settings, 1, 'Possible column misalignment', 6 );
			}
		}
		else
		{
			correction = '100%';
		}
	
		// Apply to the container elements
		divBodyStyle.width = _fnStringToCss( correction );
		divHeaderStyle.width = _fnStringToCss( correction );
	
		if ( footer ) {
			settings.nScrollFoot.style.width = _fnStringToCss( correction );
		}
	
	
		/*
		 * 4. Clean up
		 */
		if ( ! scrollY ) {
			/* IE7< puts a vertical scrollbar in place (when it shouldn't be) due to subtracting
			 * the scrollbar height from the visible display, rather than adding it on. We need to
			 * set the height in order to sort this. Don't want to do it in any other browsers.
			 */
			if ( ie67 ) {
				divBodyStyle.height = _fnStringToCss( tableEl.offsetHeight+barWidth );
			}
		}
	
		/* Finally set the width's of the header and footer tables */
		var iOuterWidth = table.outerWidth();
		divHeaderTable[0].style.width = _fnStringToCss( iOuterWidth );
		divHeaderInnerStyle.width = _fnStringToCss( iOuterWidth );
	
		// Figure out if there are scrollbar present - if so then we need a the header and footer to
		// provide a bit more space to allow "overflow" scrolling (i.e. past the scrollbar)
		var bScrolling = table.height() > divBodyEl.clientHeight || divBody.css('overflow-y') == "scroll";
		var padding = 'padding' + (browser.bScrollbarLeft ? 'Left' : 'Right' );
		divHeaderInnerStyle[ padding ] = bScrolling ? barWidth+"px" : "0px";
	
		if ( footer ) {
			divFooterTable[0].style.width = _fnStringToCss( iOuterWidth );
			divFooterInner[0].style.width = _fnStringToCss( iOuterWidth );
			divFooterInner[0].style[padding] = bScrolling ? barWidth+"px" : "0px";
		}
	
		// Correct DOM ordering for colgroup - comes before the thead
		table.children('colgroup').insertBefore( table.children('thead') );
	
		/* Adjust the position of the header in case we loose the y-scrollbar */
		divBody.scroll();
	
		// If sorting or filtering has occurred, jump the scrolling back to the top
		// only if we aren't holding the position
		if ( (settings.bSorted || settings.bFiltered) && ! settings._drawHold ) {
			divBodyEl.scrollTop = 0;
		}
	}
	
	
	
	/**
	 * Apply a given function to the display child nodes of an element array (typically
	 * TD children of TR rows
	 *  @param {function} fn Method to apply to the objects
	 *  @param array {nodes} an1 List of elements to look through for display children
	 *  @param array {nodes} an2 Another list (identical structure to the first) - optional
	 *  @memberof DataTable#oApi
	 */
	function _fnApplyToChildren( fn, an1, an2 )
	{
		var index=0, i=0, iLen=an1.length;
		var nNode1, nNode2;
	
		while ( i < iLen ) {
			nNode1 = an1[i].firstChild;
			nNode2 = an2 ? an2[i].firstChild : null;
	
			while ( nNode1 ) {
				if ( nNode1.nodeType === 1 ) {
					if ( an2 ) {
						fn( nNode1, nNode2, index );
					}
					else {
						fn( nNode1, index );
					}
	
					index++;
				}
	
				nNode1 = nNode1.nextSibling;
				nNode2 = an2 ? nNode2.nextSibling : null;
			}
	
			i++;
		}
	}
	
	
	
	var __re_html_remove = /<.*?>/g;
	
	
	/**
	 * Calculate the width of columns for the table
	 *  @param {object} oSettings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnCalculateColumnWidths ( oSettings )
	{
		var
			table = oSettings.nTable,
			columns = oSettings.aoColumns,
			scroll = oSettings.oScroll,
			scrollY = scroll.sY,
			scrollX = scroll.sX,
			scrollXInner = scroll.sXInner,
			columnCount = columns.length,
			visibleColumns = _fnGetColumns( oSettings, 'bVisible' ),
			headerCells = $('th', oSettings.nTHead),
			tableWidthAttr = table.getAttribute('width'), // from DOM element
			tableContainer = table.parentNode,
			userInputs = false,
			i, column, columnIdx, width, outerWidth,
			browser = oSettings.oBrowser,
			ie67 = browser.bScrollOversize;
	
		var styleWidth = table.style.width;
		if ( styleWidth && styleWidth.indexOf('%') !== -1 ) {
			tableWidthAttr = styleWidth;
		}
	
		/* Convert any user input sizes into pixel sizes */
		for ( i=0 ; i<visibleColumns.length ; i++ ) {
			column = columns[ visibleColumns[i] ];
	
			if ( column.sWidth !== null ) {
				column.sWidth = _fnConvertToWidth( column.sWidthOrig, tableContainer );
	
				userInputs = true;
			}
		}
	
		/* If the number of columns in the DOM equals the number that we have to
		 * process in DataTables, then we can use the offsets that are created by
		 * the web- browser. No custom sizes can be set in order for this to happen,
		 * nor scrolling used
		 */
		if ( ie67 || ! userInputs && ! scrollX && ! scrollY &&
		     columnCount == _fnVisbleColumns( oSettings ) &&
		     columnCount == headerCells.length
		) {
			for ( i=0 ; i<columnCount ; i++ ) {
				var colIdx = _fnVisibleToColumnIndex( oSettings, i );
	
				if ( colIdx !== null ) {
					columns[ colIdx ].sWidth = _fnStringToCss( headerCells.eq(i).width() );
				}
			}
		}
		else
		{
			// Otherwise construct a single row, worst case, table with the widest
			// node in the data, assign any user defined widths, then insert it into
			// the DOM and allow the browser to do all the hard work of calculating
			// table widths
			var tmpTable = $(table).clone() // don't use cloneNode - IE8 will remove events on the main table
				.css( 'visibility', 'hidden' )
				.removeAttr( 'id' );
	
			// Clean up the table body
			tmpTable.find('tbody tr').remove();
			var tr = $('<tr/>').appendTo( tmpTable.find('tbody') );
	
			// Clone the table header and footer - we can't use the header / footer
			// from the cloned table, since if scrolling is active, the table's
			// real header and footer are contained in different table tags
			tmpTable.find('thead, tfoot').remove();
			tmpTable
				.append( $(oSettings.nTHead).clone() )
				.append( $(oSettings.nTFoot).clone() );
	
			// Remove any assigned widths from the footer (from scrolling)
			tmpTable.find('tfoot th, tfoot td').css('width', '');
	
			// Apply custom sizing to the cloned header
			headerCells = _fnGetUniqueThs( oSettings, tmpTable.find('thead')[0] );
	
			for ( i=0 ; i<visibleColumns.length ; i++ ) {
				column = columns[ visibleColumns[i] ];
	
				headerCells[i].style.width = column.sWidthOrig !== null && column.sWidthOrig !== '' ?
					_fnStringToCss( column.sWidthOrig ) :
					'';
	
				// For scrollX we need to force the column width otherwise the
				// browser will collapse it. If this width is smaller than the
				// width the column requires, then it will have no effect
				if ( column.sWidthOrig && scrollX ) {
					$( headerCells[i] ).append( $('<div/>').css( {
						width: column.sWidthOrig,
						margin: 0,
						padding: 0,
						border: 0,
						height: 1
					} ) );
				}
			}
	
			// Find the widest cell for each column and put it into the table
			if ( oSettings.aoData.length ) {
				for ( i=0 ; i<visibleColumns.length ; i++ ) {
					columnIdx = visibleColumns[i];
					column = columns[ columnIdx ];
	
					$( _fnGetWidestNode( oSettings, columnIdx ) )
						.clone( false )
						.append( column.sContentPadding )
						.appendTo( tr );
				}
			}
	
			// Tidy the temporary table - remove name attributes so there aren't
			// duplicated in the dom (radio elements for example)
			$('[name]', tmpTable).removeAttr('name');
	
			// Table has been built, attach to the document so we can work with it.
			// A holding element is used, positioned at the top of the container
			// with minimal height, so it has no effect on if the container scrolls
			// or not. Otherwise it might trigger scrolling when it actually isn't
			// needed
			var holder = $('<div/>').css( scrollX || scrollY ?
					{
						position: 'absolute',
						top: 0,
						left: 0,
						height: 1,
						right: 0,
						overflow: 'hidden'
					} :
					{}
				)
				.append( tmpTable )
				.appendTo( tableContainer );
	
			// When scrolling (X or Y) we want to set the width of the table as 
			// appropriate. However, when not scrolling leave the table width as it
			// is. This results in slightly different, but I think correct behaviour
			if ( scrollX && scrollXInner ) {
				tmpTable.width( scrollXInner );
			}
			else if ( scrollX ) {
				tmpTable.css( 'width', 'auto' );
				tmpTable.removeAttr('width');
	
				// If there is no width attribute or style, then allow the table to
				// collapse
				if ( tmpTable.width() < tableContainer.clientWidth && tableWidthAttr ) {
					tmpTable.width( tableContainer.clientWidth );
				}
			}
			else if ( scrollY ) {
				tmpTable.width( tableContainer.clientWidth );
			}
			else if ( tableWidthAttr ) {
				tmpTable.width( tableWidthAttr );
			}
	
			// Get the width of each column in the constructed table - we need to
			// know the inner width (so it can be assigned to the other table's
			// cells) and the outer width so we can calculate the full width of the
			// table. This is safe since DataTables requires a unique cell for each
			// column, but if ever a header can span multiple columns, this will
			// need to be modified.
			var total = 0;
			for ( i=0 ; i<visibleColumns.length ; i++ ) {
				var cell = $(headerCells[i]);
				var border = cell.outerWidth() - cell.width();
	
				// Use getBounding... where possible (not IE8-) because it can give
				// sub-pixel accuracy, which we then want to round up!
				var bounding = browser.bBounding ?
					Math.ceil( headerCells[i].getBoundingClientRect().width ) :
					cell.outerWidth();
	
				// Total is tracked to remove any sub-pixel errors as the outerWidth
				// of the table might not equal the total given here (IE!).
				total += bounding;
	
				// Width for each column to use
				columns[ visibleColumns[i] ].sWidth = _fnStringToCss( bounding - border );
			}
	
			table.style.width = _fnStringToCss( total );
	
			// Finished with the table - ditch it
			holder.remove();
		}
	
		// If there is a width attr, we want to attach an event listener which
		// allows the table sizing to automatically adjust when the window is
		// resized. Use the width attr rather than CSS, since we can't know if the
		// CSS is a relative value or absolute - DOM read is always px.
		if ( tableWidthAttr ) {
			table.style.width = _fnStringToCss( tableWidthAttr );
		}
	
		if ( (tableWidthAttr || scrollX) && ! oSettings._reszEvt ) {
			var bindResize = function () {
				$(window).on('resize.DT-'+oSettings.sInstance, _fnThrottle( function () {
					_fnAdjustColumnSizing( oSettings );
				} ) );
			};
	
			// IE6/7 will crash if we bind a resize event handler on page load.
			// To be removed in 1.11 which drops IE6/7 support
			if ( ie67 ) {
				setTimeout( bindResize, 1000 );
			}
			else {
				bindResize();
			}
	
			oSettings._reszEvt = true;
		}
	}
	
	
	/**
	 * Throttle the calls to a function. Arguments and context are maintained for
	 * the throttled function
	 *  @param {function} fn Function to be called
	 *  @param {int} [freq=200] call frequency in mS
	 *  @returns {function} wrapped function
	 *  @memberof DataTable#oApi
	 */
	var _fnThrottle = DataTable.util.throttle;
	
	
	/**
	 * Convert a CSS unit width to pixels (e.g. 2em)
	 *  @param {string} width width to be converted
	 *  @param {node} parent parent to get the with for (required for relative widths) - optional
	 *  @returns {int} width in pixels
	 *  @memberof DataTable#oApi
	 */
	function _fnConvertToWidth ( width, parent )
	{
		if ( ! width ) {
			return 0;
		}
	
		var n = $('<div/>')
			.css( 'width', _fnStringToCss( width ) )
			.appendTo( parent || document.body );
	
		var val = n[0].offsetWidth;
		n.remove();
	
		return val;
	}
	
	
	/**
	 * Get the widest node
	 *  @param {object} settings dataTables settings object
	 *  @param {int} colIdx column of interest
	 *  @returns {node} widest table node
	 *  @memberof DataTable#oApi
	 */
	function _fnGetWidestNode( settings, colIdx )
	{
		var idx = _fnGetMaxLenString( settings, colIdx );
		if ( idx < 0 ) {
			return null;
		}
	
		var data = settings.aoData[ idx ];
		return ! data.nTr ? // Might not have been created when deferred rendering
			$('<td/>').html( _fnGetCellData( settings, idx, colIdx, 'display' ) )[0] :
			data.anCells[ colIdx ];
	}
	
	
	/**
	 * Get the maximum strlen for each data column
	 *  @param {object} settings dataTables settings object
	 *  @param {int} colIdx column of interest
	 *  @returns {string} max string length for each column
	 *  @memberof DataTable#oApi
	 */
	function _fnGetMaxLenString( settings, colIdx )
	{
		var s, max=-1, maxIdx = -1;
	
		for ( var i=0, ien=settings.aoData.length ; i<ien ; i++ ) {
			s = _fnGetCellData( settings, i, colIdx, 'display' )+'';
			s = s.replace( __re_html_remove, '' );
			s = s.replace( /&nbsp;/g, ' ' );
	
			if ( s.length > max ) {
				max = s.length;
				maxIdx = i;
			}
		}
	
		return maxIdx;
	}
	
	
	/**
	 * Append a CSS unit (only if required) to a string
	 *  @param {string} value to css-ify
	 *  @returns {string} value with css unit
	 *  @memberof DataTable#oApi
	 */
	function _fnStringToCss( s )
	{
		if ( s === null ) {
			return '0px';
		}
	
		if ( typeof s == 'number' ) {
			return s < 0 ?
				'0px' :
				s+'px';
		}
	
		// Check it has a unit character already
		return s.match(/\d$/) ?
			s+'px' :
			s;
	}
	
	
	
	function _fnSortFlatten ( settings )
	{
		var
			i, iLen, k, kLen,
			aSort = [],
			aiOrig = [],
			aoColumns = settings.aoColumns,
			aDataSort, iCol, sType, srcCol,
			fixed = settings.aaSortingFixed,
			fixedObj = $.isPlainObject( fixed ),
			nestedSort = [],
			add = function ( a ) {
				if ( a.length && ! $.isArray( a[0] ) ) {
					// 1D array
					nestedSort.push( a );
				}
				else {
					// 2D array
					$.merge( nestedSort, a );
				}
			};
	
		// Build the sort array, with pre-fix and post-fix options if they have been
		// specified
		if ( $.isArray( fixed ) ) {
			add( fixed );
		}
	
		if ( fixedObj && fixed.pre ) {
			add( fixed.pre );
		}
	
		add( settings.aaSorting );
	
		if (fixedObj && fixed.post ) {
			add( fixed.post );
		}
	
		for ( i=0 ; i<nestedSort.length ; i++ )
		{
			srcCol = nestedSort[i][0];
			aDataSort = aoColumns[ srcCol ].aDataSort;
	
			for ( k=0, kLen=aDataSort.length ; k<kLen ; k++ )
			{
				iCol = aDataSort[k];
				sType = aoColumns[ iCol ].sType || 'string';
	
				if ( nestedSort[i]._idx === undefined ) {
					nestedSort[i]._idx = $.inArray( nestedSort[i][1], aoColumns[iCol].asSorting );
				}
	
				aSort.push( {
					src:       srcCol,
					col:       iCol,
					dir:       nestedSort[i][1],
					index:     nestedSort[i]._idx,
					type:      sType,
					formatter: DataTable.ext.type.order[ sType+"-pre" ]
				} );
			}
		}
	
		return aSort;
	}
	
	/**
	 * Change the order of the table
	 *  @param {object} oSettings dataTables settings object
	 *  @memberof DataTable#oApi
	 *  @todo This really needs split up!
	 */
	function _fnSort ( oSettings )
	{
		var
			i, ien, iLen, j, jLen, k, kLen,
			sDataType, nTh,
			aiOrig = [],
			oExtSort = DataTable.ext.type.order,
			aoData = oSettings.aoData,
			aoColumns = oSettings.aoColumns,
			aDataSort, data, iCol, sType, oSort,
			formatters = 0,
			sortCol,
			displayMaster = oSettings.aiDisplayMaster,
			aSort;
	
		// Resolve any column types that are unknown due to addition or invalidation
		// @todo Can this be moved into a 'data-ready' handler which is called when
		//   data is going to be used in the table?
		_fnColumnTypes( oSettings );
	
		aSort = _fnSortFlatten( oSettings );
	
		for ( i=0, ien=aSort.length ; i<ien ; i++ ) {
			sortCol = aSort[i];
	
			// Track if we can use the fast sort algorithm
			if ( sortCol.formatter ) {
				formatters++;
			}
	
			// Load the data needed for the sort, for each cell
			_fnSortData( oSettings, sortCol.col );
		}
	
		/* No sorting required if server-side or no sorting array */
		if ( _fnDataSource( oSettings ) != 'ssp' && aSort.length !== 0 )
		{
			// Create a value - key array of the current row positions such that we can use their
			// current position during the sort, if values match, in order to perform stable sorting
			for ( i=0, iLen=displayMaster.length ; i<iLen ; i++ ) {
				aiOrig[ displayMaster[i] ] = i;
			}
	
			/* Do the sort - here we want multi-column sorting based on a given data source (column)
			 * and sorting function (from oSort) in a certain direction. It's reasonably complex to
			 * follow on it's own, but this is what we want (example two column sorting):
			 *  fnLocalSorting = function(a,b){
			 *    var iTest;
			 *    iTest = oSort['string-asc']('data11', 'data12');
			 *      if (iTest !== 0)
			 *        return iTest;
			 *    iTest = oSort['numeric-desc']('data21', 'data22');
			 *    if (iTest !== 0)
			 *      return iTest;
			 *    return oSort['numeric-asc']( aiOrig[a], aiOrig[b] );
			 *  }
			 * Basically we have a test for each sorting column, if the data in that column is equal,
			 * test the next column. If all columns match, then we use a numeric sort on the row
			 * positions in the original data array to provide a stable sort.
			 *
			 * Note - I know it seems excessive to have two sorting methods, but the first is around
			 * 15% faster, so the second is only maintained for backwards compatibility with sorting
			 * methods which do not have a pre-sort formatting function.
			 */
			if ( formatters === aSort.length ) {
				// All sort types have formatting functions
				displayMaster.sort( function ( a, b ) {
					var
						x, y, k, test, sort,
						len=aSort.length,
						dataA = aoData[a]._aSortData,
						dataB = aoData[b]._aSortData;
	
					for ( k=0 ; k<len ; k++ ) {
						sort = aSort[k];
	
						x = dataA[ sort.col ];
						y = dataB[ sort.col ];
	
						test = x<y ? -1 : x>y ? 1 : 0;
						if ( test !== 0 ) {
							return sort.dir === 'asc' ? test : -test;
						}
					}
	
					x = aiOrig[a];
					y = aiOrig[b];
					return x<y ? -1 : x>y ? 1 : 0;
				} );
			}
			else {
				// Depreciated - remove in 1.11 (providing a plug-in option)
				// Not all sort types have formatting methods, so we have to call their sorting
				// methods.
				displayMaster.sort( function ( a, b ) {
					var
						x, y, k, l, test, sort, fn,
						len=aSort.length,
						dataA = aoData[a]._aSortData,
						dataB = aoData[b]._aSortData;
	
					for ( k=0 ; k<len ; k++ ) {
						sort = aSort[k];
	
						x = dataA[ sort.col ];
						y = dataB[ sort.col ];
	
						fn = oExtSort[ sort.type+"-"+sort.dir ] || oExtSort[ "string-"+sort.dir ];
						test = fn( x, y );
						if ( test !== 0 ) {
							return test;
						}
					}
	
					x = aiOrig[a];
					y = aiOrig[b];
					return x<y ? -1 : x>y ? 1 : 0;
				} );
			}
		}
	
		/* Tell the draw function that we have sorted the data */
		oSettings.bSorted = true;
	}
	
	
	function _fnSortAria ( settings )
	{
		var label;
		var nextSort;
		var columns = settings.aoColumns;
		var aSort = _fnSortFlatten( settings );
		var oAria = settings.oLanguage.oAria;
	
		// ARIA attributes - need to loop all columns, to update all (removing old
		// attributes as needed)
		for ( var i=0, iLen=columns.length ; i<iLen ; i++ )
		{
			var col = columns[i];
			var asSorting = col.asSorting;
			var sTitle = col.sTitle.replace( /<.*?>/g, "" );
			var th = col.nTh;
	
			// IE7 is throwing an error when setting these properties with jQuery's
			// attr() and removeAttr() methods...
			th.removeAttribute('aria-sort');
	
			/* In ARIA only the first sorting column can be marked as sorting - no multi-sort option */
			if ( col.bSortable ) {
				if ( aSort.length > 0 && aSort[0].col == i ) {
					th.setAttribute('aria-sort', aSort[0].dir=="asc" ? "ascending" : "descending" );
					nextSort = asSorting[ aSort[0].index+1 ] || asSorting[0];
				}
				else {
					nextSort = asSorting[0];
				}
	
				label = sTitle + ( nextSort === "asc" ?
					oAria.sSortAscending :
					oAria.sSortDescending
				);
			}
			else {
				label = sTitle;
			}
	
			th.setAttribute('aria-label', label);
		}
	}
	
	
	/**
	 * Function to run on user sort request
	 *  @param {object} settings dataTables settings object
	 *  @param {node} attachTo node to attach the handler to
	 *  @param {int} colIdx column sorting index
	 *  @param {boolean} [append=false] Append the requested sort to the existing
	 *    sort if true (i.e. multi-column sort)
	 *  @param {function} [callback] callback function
	 *  @memberof DataTable#oApi
	 */
	function _fnSortListener ( settings, colIdx, append, callback )
	{
		var col = settings.aoColumns[ colIdx ];
		var sorting = settings.aaSorting;
		var asSorting = col.asSorting;
		var nextSortIdx;
		var next = function ( a, overflow ) {
			var idx = a._idx;
			if ( idx === undefined ) {
				idx = $.inArray( a[1], asSorting );
			}
	
			return idx+1 < asSorting.length ?
				idx+1 :
				overflow ?
					null :
					0;
		};
	
		// Convert to 2D array if needed
		if ( typeof sorting[0] === 'number' ) {
			sorting = settings.aaSorting = [ sorting ];
		}
	
		// If appending the sort then we are multi-column sorting
		if ( append && settings.oFeatures.bSortMulti ) {
			// Are we already doing some kind of sort on this column?
			var sortIdx = $.inArray( colIdx, _pluck(sorting, '0') );
	
			if ( sortIdx !== -1 ) {
				// Yes, modify the sort
				nextSortIdx = next( sorting[sortIdx], true );
	
				if ( nextSortIdx === null && sorting.length === 1 ) {
					nextSortIdx = 0; // can't remove sorting completely
				}
	
				if ( nextSortIdx === null ) {
					sorting.splice( sortIdx, 1 );
				}
				else {
					sorting[sortIdx][1] = asSorting[ nextSortIdx ];
					sorting[sortIdx]._idx = nextSortIdx;
				}
			}
			else {
				// No sort on this column yet
				sorting.push( [ colIdx, asSorting[0], 0 ] );
				sorting[sorting.length-1]._idx = 0;
			}
		}
		else if ( sorting.length && sorting[0][0] == colIdx ) {
			// Single column - already sorting on this column, modify the sort
			nextSortIdx = next( sorting[0] );
	
			sorting.length = 1;
			sorting[0][1] = asSorting[ nextSortIdx ];
			sorting[0]._idx = nextSortIdx;
		}
		else {
			// Single column - sort only on this column
			sorting.length = 0;
			sorting.push( [ colIdx, asSorting[0] ] );
			sorting[0]._idx = 0;
		}
	
		// Run the sort by calling a full redraw
		_fnReDraw( settings );
	
		// callback used for async user interaction
		if ( typeof callback == 'function' ) {
			callback( settings );
		}
	}
	
	
	/**
	 * Attach a sort handler (click) to a node
	 *  @param {object} settings dataTables settings object
	 *  @param {node} attachTo node to attach the handler to
	 *  @param {int} colIdx column sorting index
	 *  @param {function} [callback] callback function
	 *  @memberof DataTable#oApi
	 */
	function _fnSortAttachListener ( settings, attachTo, colIdx, callback )
	{
		var col = settings.aoColumns[ colIdx ];
	
		_fnBindAction( attachTo, {}, function (e) {
			/* If the column is not sortable - don't to anything */
			if ( col.bSortable === false ) {
				return;
			}
	
			// If processing is enabled use a timeout to allow the processing
			// display to be shown - otherwise to it synchronously
			if ( settings.oFeatures.bProcessing ) {
				_fnProcessingDisplay( settings, true );
	
				setTimeout( function() {
					_fnSortListener( settings, colIdx, e.shiftKey, callback );
	
					// In server-side processing, the draw callback will remove the
					// processing display
					if ( _fnDataSource( settings ) !== 'ssp' ) {
						_fnProcessingDisplay( settings, false );
					}
				}, 0 );
			}
			else {
				_fnSortListener( settings, colIdx, e.shiftKey, callback );
			}
		} );
	}
	
	
	/**
	 * Set the sorting classes on table's body, Note: it is safe to call this function
	 * when bSort and bSortClasses are false
	 *  @param {object} oSettings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnSortingClasses( settings )
	{
		var oldSort = settings.aLastSort;
		var sortClass = settings.oClasses.sSortColumn;
		var sort = _fnSortFlatten( settings );
		var features = settings.oFeatures;
		var i, ien, colIdx;
	
		if ( features.bSort && features.bSortClasses ) {
			// Remove old sorting classes
			for ( i=0, ien=oldSort.length ; i<ien ; i++ ) {
				colIdx = oldSort[i].src;
	
				// Remove column sorting
				$( _pluck( settings.aoData, 'anCells', colIdx ) )
					.removeClass( sortClass + (i<2 ? i+1 : 3) );
			}
	
			// Add new column sorting
			for ( i=0, ien=sort.length ; i<ien ; i++ ) {
				colIdx = sort[i].src;
	
				$( _pluck( settings.aoData, 'anCells', colIdx ) )
					.addClass( sortClass + (i<2 ? i+1 : 3) );
			}
		}
	
		settings.aLastSort = sort;
	}
	
	
	// Get the data to sort a column, be it from cache, fresh (populating the
	// cache), or from a sort formatter
	function _fnSortData( settings, idx )
	{
		// Custom sorting function - provided by the sort data type
		var column = settings.aoColumns[ idx ];
		var customSort = DataTable.ext.order[ column.sSortDataType ];
		var customData;
	
		if ( customSort ) {
			customData = customSort.call( settings.oInstance, settings, idx,
				_fnColumnIndexToVisible( settings, idx )
			);
		}
	
		// Use / populate cache
		var row, cellData;
		var formatter = DataTable.ext.type.order[ column.sType+"-pre" ];
	
		for ( var i=0, ien=settings.aoData.length ; i<ien ; i++ ) {
			row = settings.aoData[i];
	
			if ( ! row._aSortData ) {
				row._aSortData = [];
			}
	
			if ( ! row._aSortData[idx] || customSort ) {
				cellData = customSort ?
					customData[i] : // If there was a custom sort function, use data from there
					_fnGetCellData( settings, i, idx, 'sort' );
	
				row._aSortData[ idx ] = formatter ?
					formatter( cellData ) :
					cellData;
			}
		}
	}
	
	
	
	/**
	 * Save the state of a table
	 *  @param {object} oSettings dataTables settings object
	 *  @memberof DataTable#oApi
	 */
	function _fnSaveState ( settings )
	{
		if ( !settings.oFeatures.bStateSave || settings.bDestroying )
		{
			return;
		}
	
		/* Store the interesting variables */
		var state = {
			time:    +new Date(),
			start:   settings._iDisplayStart,
			length:  settings._iDisplayLength,
			order:   $.extend( true, [], settings.aaSorting ),
			search:  _fnSearchToCamel( settings.oPreviousSearch ),
			columns: $.map( settings.aoColumns, function ( col, i ) {
				return {
					visible: col.bVisible,
					search: _fnSearchToCamel( settings.aoPreSearchCols[i] )
				};
			} )
		};
	
		_fnCallbackFire( settings, "aoStateSaveParams", 'stateSaveParams', [settings, state] );
	
		settings.oSavedState = state;
		settings.fnStateSaveCallback.call( settings.oInstance, settings, state );
	}
	
	
	/**
	 * Attempt to load a saved table state
	 *  @param {object} oSettings dataTables settings object
	 *  @param {object} oInit DataTables init object so we can override settings
	 *  @param {function} callback Callback to execute when the state has been loaded
	 *  @memberof DataTable#oApi
	 */
	function _fnLoadState ( settings, oInit, callback )
	{
		var i, ien;
		var columns = settings.aoColumns;
		var loaded = function ( s ) {
			if ( ! s || ! s.time ) {
				callback();
				return;
			}
	
			// Allow custom and plug-in manipulation functions to alter the saved data set and
			// cancelling of loading by returning false
			var abStateLoad = _fnCallbackFire( settings, 'aoStateLoadParams', 'stateLoadParams', [settings, s] );
			if ( $.inArray( false, abStateLoad ) !== -1 ) {
				callback();
				return;
			}
	
			// Reject old data
			var duration = settings.iStateDuration;
			if ( duration > 0 && s.time < +new Date() - (duration*1000) ) {
				callback();
				return;
			}
	
			// Number of columns have changed - all bets are off, no restore of settings
			if ( s.columns && columns.length !== s.columns.length ) {
				callback();
				return;
			}
	
			// Store the saved state so it might be accessed at any time
			settings.oLoadedState = $.extend( true, {}, s );
	
			// Restore key features - todo - for 1.11 this needs to be done by
			// subscribed events
			if ( s.start !== undefined ) {
				settings._iDisplayStart    = s.start;
				settings.iInitDisplayStart = s.start;
			}
			if ( s.length !== undefined ) {
				settings._iDisplayLength   = s.length;
			}
	
			// Order
			if ( s.order !== undefined ) {
				settings.aaSorting = [];
				$.each( s.order, function ( i, col ) {
					settings.aaSorting.push( col[0] >= columns.length ?
						[ 0, col[1] ] :
						col
					);
				} );
			}
	
			// Search
			if ( s.search !== undefined ) {
				$.extend( settings.oPreviousSearch, _fnSearchToHung( s.search ) );
			}
	
			// Columns
			//
			if ( s.columns ) {
				for ( i=0, ien=s.columns.length ; i<ien ; i++ ) {
					var col = s.columns[i];
	
					// Visibility
					if ( col.visible !== undefined ) {
						columns[i].bVisible = col.visible;
					}
	
					// Search
					if ( col.search !== undefined ) {
						$.extend( settings.aoPreSearchCols[i], _fnSearchToHung( col.search ) );
					}
				}
			}
	
			_fnCallbackFire( settings, 'aoStateLoaded', 'stateLoaded', [settings, s] );
			callback();
		}
	
		if ( ! settings.oFeatures.bStateSave ) {
			callback();
			return;
		}
	
		var state = settings.fnStateLoadCallback.call( settings.oInstance, settings, loaded );
	
		if ( state !== undefined ) {
			loaded( state );
		}
		// otherwise, wait for the loaded callback to be executed
	}
	
	
	/**
	 * Return the settings object for a particular table
	 *  @param {node} table table we are using as a dataTable
	 *  @returns {object} Settings object - or null if not found
	 *  @memberof DataTable#oApi
	 */
	function _fnSettingsFromNode ( table )
	{
		var settings = DataTable.settings;
		var idx = $.inArray( table, _pluck( settings, 'nTable' ) );
	
		return idx !== -1 ?
			settings[ idx ] :
			null;
	}
	
	
	/**
	 * Log an error message
	 *  @param {object} settings dataTables settings object
	 *  @param {int} level log error messages, or display them to the user
	 *  @param {string} msg error message
	 *  @param {int} tn Technical note id to get more information about the error.
	 *  @memberof DataTable#oApi
	 */
	function _fnLog( settings, level, msg, tn )
	{
		msg = 'DataTables warning: '+
			(settings ? 'table id='+settings.sTableId+' - ' : '')+msg;
	
		if ( tn ) {
			msg += '. For more information about this error, please see '+
			'http://datatables.net/tn/'+tn;
		}
	
		if ( ! level  ) {
			// Backwards compatibility pre 1.10
			var ext = DataTable.ext;
			var type = ext.sErrMode || ext.errMode;
	
			if ( settings ) {
				_fnCallbackFire( settings, null, 'error', [ settings, tn, msg ] );
			}
	
			if ( type == 'alert' ) {
				alert( msg );
			}
			else if ( type == 'throw' ) {
				throw new Error(msg);
			}
			else if ( typeof type == 'function' ) {
				type( settings, tn, msg );
			}
		}
		else if ( window.console && console.log ) {
			console.log( msg );
		}
	}
	
	
	/**
	 * See if a property is defined on one object, if so assign it to the other object
	 *  @param {object} ret target object
	 *  @param {object} src source object
	 *  @param {string} name property
	 *  @param {string} [mappedName] name to map too - optional, name used if not given
	 *  @memberof DataTable#oApi
	 */
	function _fnMap( ret, src, name, mappedName )
	{
		if ( $.isArray( name ) ) {
			$.each( name, function (i, val) {
				if ( $.isArray( val ) ) {
					_fnMap( ret, src, val[0], val[1] );
				}
				else {
					_fnMap( ret, src, val );
				}
			} );
	
			return;
		}
	
		if ( mappedName === undefined ) {
			mappedName = name;
		}
	
		if ( src[name] !== undefined ) {
			ret[mappedName] = src[name];
		}
	}
	
	
	/**
	 * Extend objects - very similar to jQuery.extend, but deep copy objects, and
	 * shallow copy arrays. The reason we need to do this, is that we don't want to
	 * deep copy array init values (such as aaSorting) since the dev wouldn't be
	 * able to override them, but we do want to deep copy arrays.
	 *  @param {object} out Object to extend
	 *  @param {object} extender Object from which the properties will be applied to
	 *      out
	 *  @param {boolean} breakRefs If true, then arrays will be sliced to take an
	 *      independent copy with the exception of the `data` or `aaData` parameters
	 *      if they are present. This is so you can pass in a collection to
	 *      DataTables and have that used as your data source without breaking the
	 *      references
	 *  @returns {object} out Reference, just for convenience - out === the return.
	 *  @memberof DataTable#oApi
	 *  @todo This doesn't take account of arrays inside the deep copied objects.
	 */
	function _fnExtend( out, extender, breakRefs )
	{
		var val;
	
		for ( var prop in extender ) {
			if ( extender.hasOwnProperty(prop) ) {
				val = extender[prop];
	
				if ( $.isPlainObject( val ) ) {
					if ( ! $.isPlainObject( out[prop] ) ) {
						out[prop] = {};
					}
					$.extend( true, out[prop], val );
				}
				else if ( breakRefs && prop !== 'data' && prop !== 'aaData' && $.isArray(val) ) {
					out[prop] = val.slice();
				}
				else {
					out[prop] = val;
				}
			}
		}
	
		return out;
	}
	
	
	/**
	 * Bind an event handers to allow a click or return key to activate the callback.
	 * This is good for accessibility since a return on the keyboard will have the
	 * same effect as a click, if the element has focus.
	 *  @param {element} n Element to bind the action to
	 *  @param {object} oData Data object to pass to the triggered function
	 *  @param {function} fn Callback function for when the event is triggered
	 *  @memberof DataTable#oApi
	 */
	function _fnBindAction( n, oData, fn )
	{
		$(n)
			.on( 'click.DT', oData, function (e) {
					n.blur(); // Remove focus outline for mouse users
					fn(e);
				} )
			.on( 'keypress.DT', oData, function (e){
					if ( e.which === 13 ) {
						e.preventDefault();
						fn(e);
					}
				} )
			.on( 'selectstart.DT', function () {
					/* Take the brutal approach to cancelling text selection */
					return false;
				} );
	}
	
	
	/**
	 * Register a callback function. Easily allows a callback function to be added to
	 * an array store of callback functions that can then all be called together.
	 *  @param {object} oSettings dataTables settings object
	 *  @param {string} sStore Name of the array storage for the callbacks in oSettings
	 *  @param {function} fn Function to be called back
	 *  @param {string} sName Identifying name for the callback (i.e. a label)
	 *  @memberof DataTable#oApi
	 */
	function _fnCallbackReg( oSettings, sStore, fn, sName )
	{
		if ( fn )
		{
			oSettings[sStore].push( {
				"fn": fn,
				"sName": sName
			} );
		}
	}
	
	
	/**
	 * Fire callback functions and trigger events. Note that the loop over the
	 * callback array store is done backwards! Further note that you do not want to
	 * fire off triggers in time sensitive applications (for example cell creation)
	 * as its slow.
	 *  @param {object} settings dataTables settings object
	 *  @param {string} callbackArr Name of the array storage for the callbacks in
	 *      oSettings
	 *  @param {string} eventName Name of the jQuery custom event to trigger. If
	 *      null no trigger is fired
	 *  @param {array} args Array of arguments to pass to the callback function /
	 *      trigger
	 *  @memberof DataTable#oApi
	 */
	function _fnCallbackFire( settings, callbackArr, eventName, args )
	{
		var ret = [];
	
		if ( callbackArr ) {
			ret = $.map( settings[callbackArr].slice().reverse(), function (val, i) {
				return val.fn.apply( settings.oInstance, args );
			} );
		}
	
		if ( eventName !== null ) {
			var e = $.Event( eventName+'.dt' );
	
			$(settings.nTable).trigger( e, args );
	
			ret.push( e.result );
		}
	
		return ret;
	}
	
	
	function _fnLengthOverflow ( settings )
	{
		var
			start = settings._iDisplayStart,
			end = settings.fnDisplayEnd(),
			len = settings._iDisplayLength;
	
		/* If we have space to show extra rows (backing up from the end point - then do so */
		if ( start >= end )
		{
			start = end - len;
		}
	
		// Keep the start record on the current page
		start -= (start % len);
	
		if ( len === -1 || start < 0 )
		{
			start = 0;
		}
	
		settings._iDisplayStart = start;
	}
	
	
	function _fnRenderer( settings, type )
	{
		var renderer = settings.renderer;
		var host = DataTable.ext.renderer[type];
	
		if ( $.isPlainObject( renderer ) && renderer[type] ) {
			// Specific renderer for this type. If available use it, otherwise use
			// the default.
			return host[renderer[type]] || host._;
		}
		else if ( typeof renderer === 'string' ) {
			// Common renderer - if there is one available for this type use it,
			// otherwise use the default
			return host[renderer] || host._;
		}
	
		// Use the default
		return host._;
	}
	
	
	/**
	 * Detect the data source being used for the table. Used to simplify the code
	 * a little (ajax) and to make it compress a little smaller.
	 *
	 *  @param {object} settings dataTables settings object
	 *  @returns {string} Data source
	 *  @memberof DataTable#oApi
	 */
	function _fnDataSource ( settings )
	{
		if ( settings.oFeatures.bServerSide ) {
			return 'ssp';
		}
		else if ( settings.ajax || settings.sAjaxSource ) {
			return 'ajax';
		}
		return 'dom';
	}
	

	
	
	/**
	 * Computed structure of the DataTables API, defined by the options passed to
	 * `DataTable.Api.register()` when building the API.
	 *
	 * The structure is built in order to speed creation and extension of the Api
	 * objects since the extensions are effectively pre-parsed.
	 *
	 * The array is an array of objects with the following structure, where this
	 * base array represents the Api prototype base:
	 *
	 *     [
	 *       {
	 *         name:      'data'                -- string   - Property name
	 *         val:       function () {},       -- function - Api method (or undefined if just an object
	 *         methodExt: [ ... ],              -- array    - Array of Api object definitions to extend the method result
	 *         propExt:   [ ... ]               -- array    - Array of Api object definitions to extend the property
	 *       },
	 *       {
	 *         name:     'row'
	 *         val:       {},
	 *         methodExt: [ ... ],
	 *         propExt:   [
	 *           {
	 *             name:      'data'
	 *             val:       function () {},
	 *             methodExt: [ ... ],
	 *             propExt:   [ ... ]
	 *           },
	 *           ...
	 *         ]
	 *       }
	 *     ]
	 *
	 * @type {Array}
	 * @ignore
	 */
	var __apiStruct = [];
	
	
	/**
	 * `Array.prototype` reference.
	 *
	 * @type object
	 * @ignore
	 */
	var __arrayProto = Array.prototype;
	
	
	/**
	 * Abstraction for `context` parameter of the `Api` constructor to allow it to
	 * take several different forms for ease of use.
	 *
	 * Each of the input parameter types will be converted to a DataTables settings
	 * object where possible.
	 *
	 * @param  {string|node|jQuery|object} mixed DataTable identifier. Can be one
	 *   of:
	 *
	 *   * `string` - jQuery selector. Any DataTables' matching the given selector
	 *     with be found and used.
	 *   * `node` - `TABLE` node which has already been formed into a DataTable.
	 *   * `jQuery` - A jQuery object of `TABLE` nodes.
	 *   * `object` - DataTables settings object
	 *   * `DataTables.Api` - API instance
	 * @return {array|null} Matching DataTables settings objects. `null` or
	 *   `undefined` is returned if no matching DataTable is found.
	 * @ignore
	 */
	var _toSettings = function ( mixed )
	{
		var idx, jq;
		var settings = DataTable.settings;
		var tables = $.map( settings, function (el, i) {
			return el.nTable;
		} );
	
		if ( ! mixed ) {
			return [];
		}
		else if ( mixed.nTable && mixed.oApi ) {
			// DataTables settings object
			return [ mixed ];
		}
		else if ( mixed.nodeName && mixed.nodeName.toLowerCase() === 'table' ) {
			// Table node
			idx = $.inArray( mixed, tables );
			return idx !== -1 ? [ settings[idx] ] : null;
		}
		else if ( mixed && typeof mixed.settings === 'function' ) {
			return mixed.settings().toArray();
		}
		else if ( typeof mixed === 'string' ) {
			// jQuery selector
			jq = $(mixed);
		}
		else if ( mixed instanceof $ ) {
			// jQuery object (also DataTables instance)
			jq = mixed;
		}
	
		if ( jq ) {
			return jq.map( function(i) {
				idx = $.inArray( this, tables );
				return idx !== -1 ? settings[idx] : null;
			} ).toArray();
		}
	};
	
	
	/**
	 * DataTables API class - used to control and interface with  one or more
	 * DataTables enhanced tables.
	 *
	 * The API class is heavily based on jQuery, presenting a chainable interface
	 * that you can use to interact with tables. Each instance of the API class has
	 * a "context" - i.e. the tables that it will operate on. This could be a single
	 * table, all tables on a page or a sub-set thereof.
	 *
	 * Additionally the API is designed to allow you to easily work with the data in
	 * the tables, retrieving and manipulating it as required. This is done by
	 * presenting the API class as an array like interface. The contents of the
	 * array depend upon the actions requested by each method (for example
	 * `rows().nodes()` will return an array of nodes, while `rows().data()` will
	 * return an array of objects or arrays depending upon your table's
	 * configuration). The API object has a number of array like methods (`push`,
	 * `pop`, `reverse` etc) as well as additional helper methods (`each`, `pluck`,
	 * `unique` etc) to assist your working with the data held in a table.
	 *
	 * Most methods (those which return an Api instance) are chainable, which means
	 * the return from a method call also has all of the methods available that the
	 * top level object had. For example, these two calls are equivalent:
	 *
	 *     // Not chained
	 *     api.row.add( {...} );
	 *     api.draw();
	 *
	 *     // Chained
	 *     api.row.add( {...} ).draw();
	 *
	 * @class DataTable.Api
	 * @param {array|object|string|jQuery} context DataTable identifier. This is
	 *   used to define which DataTables enhanced tables this API will operate on.
	 *   Can be one of:
	 *
	 *   * `string` - jQuery selector. Any DataTables' matching the given selector
	 *     with be found and used.
	 *   * `node` - `TABLE` node which has already been formed into a DataTable.
	 *   * `jQuery` - A jQuery object of `TABLE` nodes.
	 *   * `object` - DataTables settings object
	 * @param {array} [data] Data to initialise the Api instance with.
	 *
	 * @example
	 *   // Direct initialisation during DataTables construction
	 *   var api = $('#example').DataTable();
	 *
	 * @example
	 *   // Initialisation using a DataTables jQuery object
	 *   var api = $('#example').dataTable().api();
	 *
	 * @example
	 *   // Initialisation as a constructor
	 *   var api = new $.fn.DataTable.Api( 'table.dataTable' );
	 */
	_Api = function ( context, data )
	{
		if ( ! (this instanceof _Api) ) {
			return new _Api( context, data );
		}
	
		var settings = [];
		var ctxSettings = function ( o ) {
			var a = _toSettings( o );
			if ( a ) {
				settings = settings.concat( a );
			}
		};
	
		if ( $.isArray( context ) ) {
			for ( var i=0, ien=context.length ; i<ien ; i++ ) {
				ctxSettings( context[i] );
			}
		}
		else {
			ctxSettings( context );
		}
	
		// Remove duplicates
		this.context = _unique( settings );
	
		// Initial data
		if ( data ) {
			$.merge( this, data );
		}
	
		// selector
		this.selector = {
			rows: null,
			cols: null,
			opts: null
		};
	
		_Api.extend( this, this, __apiStruct );
	};
	
	DataTable.Api = _Api;
	
	// Don't destroy the existing prototype, just extend it. Required for jQuery 2's
	// isPlainObject.
	$.extend( _Api.prototype, {
		any: function ()
		{
			return this.count() !== 0;
		},
	
	
		concat:  __arrayProto.concat,
	
	
		context: [], // array of table settings objects
	
	
		count: function ()
		{
			return this.flatten().length;
		},
	
	
		each: function ( fn )
		{
			for ( var i=0, ien=this.length ; i<ien; i++ ) {
				fn.call( this, this[i], i, this );
			}
	
			return this;
		},
	
	
		eq: function ( idx )
		{
			var ctx = this.context;
	
			return ctx.length > idx ?
				new _Api( ctx[idx], this[idx] ) :
				null;
		},
	
	
		filter: function ( fn )
		{
			var a = [];
	
			if ( __arrayProto.filter ) {
				a = __arrayProto.filter.call( this, fn, this );
			}
			else {
				// Compatibility for browsers without EMCA-252-5 (JS 1.6)
				for ( var i=0, ien=this.length ; i<ien ; i++ ) {
					if ( fn.call( this, this[i], i, this ) ) {
						a.push( this[i] );
					}
				}
			}
	
			return new _Api( this.context, a );
		},
	
	
		flatten: function ()
		{
			var a = [];
			return new _Api( this.context, a.concat.apply( a, this.toArray() ) );
		},
	
	
		join:    __arrayProto.join,
	
	
		indexOf: __arrayProto.indexOf || function (obj, start)
		{
			for ( var i=(start || 0), ien=this.length ; i<ien ; i++ ) {
				if ( this[i] === obj ) {
					return i;
				}
			}
			return -1;
		},
	
		iterator: function ( flatten, type, fn, alwaysNew ) {
			var
				a = [], ret,
				i, ien, j, jen,
				context = this.context,
				rows, items, item,
				selector = this.selector;
	
			// Argument shifting
			if ( typeof flatten === 'string' ) {
				alwaysNew = fn;
				fn = type;
				type = flatten;
				flatten = false;
			}
	
			for ( i=0, ien=context.length ; i<ien ; i++ ) {
				var apiInst = new _Api( context[i] );
	
				if ( type === 'table' ) {
					ret = fn.call( apiInst, context[i], i );
	
					if ( ret !== undefined ) {
						a.push( ret );
					}
				}
				else if ( type === 'columns' || type === 'rows' ) {
					// this has same length as context - one entry for each table
					ret = fn.call( apiInst, context[i], this[i], i );
	
					if ( ret !== undefined ) {
						a.push( ret );
					}
				}
				else if ( type === 'column' || type === 'column-rows' || type === 'row' || type === 'cell' ) {
					// columns and rows share the same structure.
					// 'this' is an array of column indexes for each context
					items = this[i];
	
					if ( type === 'column-rows' ) {
						rows = _selector_row_indexes( context[i], selector.opts );
					}
	
					for ( j=0, jen=items.length ; j<jen ; j++ ) {
						item = items[j];
	
						if ( type === 'cell' ) {
							ret = fn.call( apiInst, context[i], item.row, item.column, i, j );
						}
						else {
							ret = fn.call( apiInst, context[i], item, i, j, rows );
						}
	
						if ( ret !== undefined ) {
							a.push( ret );
						}
					}
				}
			}
	
			if ( a.length || alwaysNew ) {
				var api = new _Api( context, flatten ? a.concat.apply( [], a ) : a );
				var apiSelector = api.selector;
				apiSelector.rows = selector.rows;
				apiSelector.cols = selector.cols;
				apiSelector.opts = selector.opts;
				return api;
			}
			return this;
		},
	
	
		lastIndexOf: __arrayProto.lastIndexOf || function (obj, start)
		{
			// Bit cheeky...
			return this.indexOf.apply( this.toArray.reverse(), arguments );
		},
	
	
		length:  0,
	
	
		map: function ( fn )
		{
			var a = [];
	
			if ( __arrayProto.map ) {
				a = __arrayProto.map.call( this, fn, this );
			}
			else {
				// Compatibility for browsers without EMCA-252-5 (JS 1.6)
				for ( var i=0, ien=this.length ; i<ien ; i++ ) {
					a.push( fn.call( this, this[i], i ) );
				}
			}
	
			return new _Api( this.context, a );
		},
	
	
		pluck: function ( prop )
		{
			return this.map( function ( el ) {
				return el[ prop ];
			} );
		},
	
		pop:     __arrayProto.pop,
	
	
		push:    __arrayProto.push,
	
	
		// Does not return an API instance
		reduce: __arrayProto.reduce || function ( fn, init )
		{
			return _fnReduce( this, fn, init, 0, this.length, 1 );
		},
	
	
		reduceRight: __arrayProto.reduceRight || function ( fn, init )
		{
			return _fnReduce( this, fn, init, this.length-1, -1, -1 );
		},
	
	
		reverse: __arrayProto.reverse,
	
	
		// Object with rows, columns and opts
		selector: null,
	
	
		shift:   __arrayProto.shift,
	
	
		slice: function () {
			return new _Api( this.context, this );
		},
	
	
		sort:    __arrayProto.sort, // ? name - order?
	
	
		splice:  __arrayProto.splice,
	
	
		toArray: function ()
		{
			return __arrayProto.slice.call( this );
		},
	
	
		to$: function ()
		{
			return $( this );
		},
	
	
		toJQuery: function ()
		{
			return $( this );
		},
	
	
		unique: function ()
		{
			return new _Api( this.context, _unique(this) );
		},
	
	
		unshift: __arrayProto.unshift
	} );
	
	
	_Api.extend = function ( scope, obj, ext )
	{
		// Only extend API instances and static properties of the API
		if ( ! ext.length || ! obj || ( ! (obj instanceof _Api) && ! obj.__dt_wrapper ) ) {
			return;
		}
	
		var
			i, ien,
			j, jen,
			struct, inner,
			methodScoping = function ( scope, fn, struc ) {
				return function () {
					var ret = fn.apply( scope, arguments );
	
					// Method extension
					_Api.extend( ret, ret, struc.methodExt );
					return ret;
				};
			};
	
		for ( i=0, ien=ext.length ; i<ien ; i++ ) {
			struct = ext[i];
	
			// Value
			obj[ struct.name ] = typeof struct.val === 'function' ?
				methodScoping( scope, struct.val, struct ) :
				$.isPlainObject( struct.val ) ?
					{} :
					struct.val;
	
			obj[ struct.name ].__dt_wrapper = true;
	
			// Property extension
			_Api.extend( scope, obj[ struct.name ], struct.propExt );
		}
	};
	
	
	// @todo - Is there need for an augment function?
	// _Api.augment = function ( inst, name )
	// {
	// 	// Find src object in the structure from the name
	// 	var parts = name.split('.');
	
	// 	_Api.extend( inst, obj );
	// };
	
	
	//     [
	//       {
	//         name:      'data'                -- string   - Property name
	//         val:       function () {},       -- function - Api method (or undefined if just an object
	//         methodExt: [ ... ],              -- array    - Array of Api object definitions to extend the method result
	//         propExt:   [ ... ]               -- array    - Array of Api object definitions to extend the property
	//       },
	//       {
	//         name:     'row'
	//         val:       {},
	//         methodExt: [ ... ],
	//         propExt:   [
	//           {
	//             name:      'data'
	//             val:       function () {},
	//             methodExt: [ ... ],
	//             propExt:   [ ... ]
	//           },
	//           ...
	//         ]
	//       }
	//     ]
	
	_Api.register = _api_register = function ( name, val )
	{
		if ( $.isArray( name ) ) {
			for ( var j=0, jen=name.length ; j<jen ; j++ ) {
				_Api.register( name[j], val );
			}
			return;
		}
	
		var
			i, ien,
			heir = name.split('.'),
			struct = __apiStruct,
			key, method;
	
		var find = function ( src, name ) {
			for ( var i=0, ien=src.length ; i<ien ; i++ ) {
				if ( src[i].name === name ) {
					return src[i];
				}
			}
			return null;
		};
	
		for ( i=0, ien=heir.length ; i<ien ; i++ ) {
			method = heir[i].indexOf('()') !== -1;
			key = method ?
				heir[i].replace('()', '') :
				heir[i];
	
			var src = find( struct, key );
			if ( ! src ) {
				src = {
					name:      key,
					val:       {},
					methodExt: [],
					propExt:   []
				};
				struct.push( src );
			}
	
			if ( i === ien-1 ) {
				src.val = val;
			}
			else {
				struct = method ?
					src.methodExt :
					src.propExt;
			}
		}
	};
	
	
	_Api.registerPlural = _api_registerPlural = function ( pluralName, singularName, val ) {
		_Api.register( pluralName, val );
	
		_Api.register( singularName, function () {
			var ret = val.apply( this, arguments );
	
			if ( ret === this ) {
				// Returned item is the API instance that was passed in, return it
				return this;
			}
			else if ( ret instanceof _Api ) {
				// New API instance returned, want the value from the first item
				// in the returned array for the singular result.
				return ret.length ?
					$.isArray( ret[0] ) ?
						new _Api( ret.context, ret[0] ) : // Array results are 'enhanced'
						ret[0] :
					undefined;
			}
	
			// Non-API return - just fire it back
			return ret;
		} );
	};
	
	
	/**
	 * Selector for HTML tables. Apply the given selector to the give array of
	 * DataTables settings objects.
	 *
	 * @param {string|integer} [selector] jQuery selector string or integer
	 * @param  {array} Array of DataTables settings objects to be filtered
	 * @return {array}
	 * @ignore
	 */
	var __table_selector = function ( selector, a )
	{
		// Integer is used to pick out a table by index
		if ( typeof selector === 'number' ) {
			return [ a[ selector ] ];
		}
	
		// Perform a jQuery selector on the table nodes
		var nodes = $.map( a, function (el, i) {
			return el.nTable;
		} );
	
		return $(nodes)
			.filter( selector )
			.map( function (i) {
				// Need to translate back from the table node to the settings
				var idx = $.inArray( this, nodes );
				return a[ idx ];
			} )
			.toArray();
	};
	
	
	
	/**
	 * Context selector for the API's context (i.e. the tables the API instance
	 * refers to.
	 *
	 * @name    DataTable.Api#tables
	 * @param {string|integer} [selector] Selector to pick which tables the iterator
	 *   should operate on. If not given, all tables in the current context are
	 *   used. This can be given as a jQuery selector (for example `':gt(0)'`) to
	 *   select multiple tables or as an integer to select a single table.
	 * @returns {DataTable.Api} Returns a new API instance if a selector is given.
	 */
	_api_register( 'tables()', function ( selector ) {
		// A new instance is created if there was a selector specified
		return selector ?
			new _Api( __table_selector( selector, this.context ) ) :
			this;
	} );
	
	
	_api_register( 'table()', function ( selector ) {
		var tables = this.tables( selector );
		var ctx = tables.context;
	
		// Truncate to the first matched table
		return ctx.length ?
			new _Api( ctx[0] ) :
			tables;
	} );
	
	
	_api_registerPlural( 'tables().nodes()', 'table().node()' , function () {
		return this.iterator( 'table', function ( ctx ) {
			return ctx.nTable;
		}, 1 );
	} );
	
	
	_api_registerPlural( 'tables().body()', 'table().body()' , function () {
		return this.iterator( 'table', function ( ctx ) {
			return ctx.nTBody;
		}, 1 );
	} );
	
	
	_api_registerPlural( 'tables().header()', 'table().header()' , function () {
		return this.iterator( 'table', function ( ctx ) {
			return ctx.nTHead;
		}, 1 );
	} );
	
	
	_api_registerPlural( 'tables().footer()', 'table().footer()' , function () {
		return this.iterator( 'table', function ( ctx ) {
			return ctx.nTFoot;
		}, 1 );
	} );
	
	
	_api_registerPlural( 'tables().containers()', 'table().container()' , function () {
		return this.iterator( 'table', function ( ctx ) {
			return ctx.nTableWrapper;
		}, 1 );
	} );
	
	
	
	/**
	 * Redraw the tables in the current context.
	 */
	_api_register( 'draw()', function ( paging ) {
		return this.iterator( 'table', function ( settings ) {
			if ( paging === 'page' ) {
				_fnDraw( settings );
			}
			else {
				if ( typeof paging === 'string' ) {
					paging = paging === 'full-hold' ?
						false :
						true;
				}
	
				_fnReDraw( settings, paging===false );
			}
		} );
	} );
	
	
	
	/**
	 * Get the current page index.
	 *
	 * @return {integer} Current page index (zero based)
	 *//**
	 * Set the current page.
	 *
	 * Note that if you attempt to show a page which does not exist, DataTables will
	 * not throw an error, but rather reset the paging.
	 *
	 * @param {integer|string} action The paging action to take. This can be one of:
	 *  * `integer` - The page index to jump to
	 *  * `string` - An action to take:
	 *    * `first` - Jump to first page.
	 *    * `next` - Jump to the next page
	 *    * `previous` - Jump to previous page
	 *    * `last` - Jump to the last page.
	 * @returns {DataTables.Api} this
	 */
	_api_register( 'page()', function ( action ) {
		if ( action === undefined ) {
			return this.page.info().page; // not an expensive call
		}
	
		// else, have an action to take on all tables
		return this.iterator( 'table', function ( settings ) {
			_fnPageChange( settings, action );
		} );
	} );
	
	
	/**
	 * Paging information for the first table in the current context.
	 *
	 * If you require paging information for another table, use the `table()` method
	 * with a suitable selector.
	 *
	 * @return {object} Object with the following properties set:
	 *  * `page` - Current page index (zero based - i.e. the first page is `0`)
	 *  * `pages` - Total number of pages
	 *  * `start` - Display index for the first record shown on the current page
	 *  * `end` - Display index for the last record shown on the current page
	 *  * `length` - Display length (number of records). Note that generally `start
	 *    + length = end`, but this is not always true, for example if there are
	 *    only 2 records to show on the final page, with a length of 10.
	 *  * `recordsTotal` - Full data set length
	 *  * `recordsDisplay` - Data set length once the current filtering criterion
	 *    are applied.
	 */
	_api_register( 'page.info()', function ( action ) {
		if ( this.context.length === 0 ) {
			return undefined;
		}
	
		var
			settings   = this.context[0],
			start      = settings._iDisplayStart,
			len        = settings.oFeatures.bPaginate ? settings._iDisplayLength : -1,
			visRecords = settings.fnRecordsDisplay(),
			all        = len === -1;
	
		return {
			"page":           all ? 0 : Math.floor( start / len ),
			"pages":          all ? 1 : Math.ceil( visRecords / len ),
			"start":          start,
			"end":            settings.fnDisplayEnd(),
			"length":         len,
			"recordsTotal":   settings.fnRecordsTotal(),
			"recordsDisplay": visRecords,
			"serverSide":     _fnDataSource( settings ) === 'ssp'
		};
	} );
	
	
	/**
	 * Get the current page length.
	 *
	 * @return {integer} Current page length. Note `-1` indicates that all records
	 *   are to be shown.
	 *//**
	 * Set the current page length.
	 *
	 * @param {integer} Page length to set. Use `-1` to show all records.
	 * @returns {DataTables.Api} this
	 */
	_api_register( 'page.len()', function ( len ) {
		// Note that we can't call this function 'length()' because `length`
		// is a Javascript property of functions which defines how many arguments
		// the function expects.
		if ( len === undefined ) {
			return this.context.length !== 0 ?
				this.context[0]._iDisplayLength :
				undefined;
		}
	
		// else, set the page length
		return this.iterator( 'table', function ( settings ) {
			_fnLengthChange( settings, len );
		} );
	} );
	
	
	
	var __reload = function ( settings, holdPosition, callback ) {
		// Use the draw event to trigger a callback
		if ( callback ) {
			var api = new _Api( settings );
	
			api.one( 'draw', function () {
				callback( api.ajax.json() );
			} );
		}
	
		if ( _fnDataSource( settings ) == 'ssp' ) {
			_fnReDraw( settings, holdPosition );
		}
		else {
			_fnProcessingDisplay( settings, true );
	
			// Cancel an existing request
			var xhr = settings.jqXHR;
			if ( xhr && xhr.readyState !== 4 ) {
				xhr.abort();
			}
	
			// Trigger xhr
			_fnBuildAjax( settings, [], function( json ) {
				_fnClearTable( settings );
	
				var data = _fnAjaxDataSrc( settings, json );
				for ( var i=0, ien=data.length ; i<ien ; i++ ) {
					_fnAddData( settings, data[i] );
				}
	
				_fnReDraw( settings, holdPosition );
				_fnProcessingDisplay( settings, false );
			} );
		}
	};
	
	
	/**
	 * Get the JSON response from the last Ajax request that DataTables made to the
	 * server. Note that this returns the JSON from the first table in the current
	 * context.
	 *
	 * @return {object} JSON received from the server.
	 */
	_api_register( 'ajax.json()', function () {
		var ctx = this.context;
	
		if ( ctx.length > 0 ) {
			return ctx[0].json;
		}
	
		// else return undefined;
	} );
	
	
	/**
	 * Get the data submitted in the last Ajax request
	 */
	_api_register( 'ajax.params()', function () {
		var ctx = this.context;
	
		if ( ctx.length > 0 ) {
			return ctx[0].oAjaxData;
		}
	
		// else return undefined;
	} );
	
	
	/**
	 * Reload tables from the Ajax data source. Note that this function will
	 * automatically re-draw the table when the remote data has been loaded.
	 *
	 * @param {boolean} [reset=true] Reset (default) or hold the current paging
	 *   position. A full re-sort and re-filter is performed when this method is
	 *   called, which is why the pagination reset is the default action.
	 * @returns {DataTables.Api} this
	 */
	_api_register( 'ajax.reload()', function ( callback, resetPaging ) {
		return this.iterator( 'table', function (settings) {
			__reload( settings, resetPaging===false, callback );
		} );
	} );
	
	
	/**
	 * Get the current Ajax URL. Note that this returns the URL from the first
	 * table in the current context.
	 *
	 * @return {string} Current Ajax source URL
	 *//**
	 * Set the Ajax URL. Note that this will set the URL for all tables in the
	 * current context.
	 *
	 * @param {string} url URL to set.
	 * @returns {DataTables.Api} this
	 */
	_api_register( 'ajax.url()', function ( url ) {
		var ctx = this.context;
	
		if ( url === undefined ) {
			// get
			if ( ctx.length === 0 ) {
				return undefined;
			}
			ctx = ctx[0];
	
			return ctx.ajax ?
				$.isPlainObject( ctx.ajax ) ?
					ctx.ajax.url :
					ctx.ajax :
				ctx.sAjaxSource;
		}
	
		// set
		return this.iterator( 'table', function ( settings ) {
			if ( $.isPlainObject( settings.ajax ) ) {
				settings.ajax.url = url;
			}
			else {
				settings.ajax = url;
			}
			// No need to consider sAjaxSource here since DataTables gives priority
			// to `ajax` over `sAjaxSource`. So setting `ajax` here, renders any
			// value of `sAjaxSource` redundant.
		} );
	} );
	
	
	/**
	 * Load data from the newly set Ajax URL. Note that this method is only
	 * available when `ajax.url()` is used to set a URL. Additionally, this method
	 * has the same effect as calling `ajax.reload()` but is provided for
	 * convenience when setting a new URL. Like `ajax.reload()` it will
	 * automatically redraw the table once the remote data has been loaded.
	 *
	 * @returns {DataTables.Api} this
	 */
	_api_register( 'ajax.url().load()', function ( callback, resetPaging ) {
		// Same as a reload, but makes sense to present it for easy access after a
		// url change
		return this.iterator( 'table', function ( ctx ) {
			__reload( ctx, resetPaging===false, callback );
		} );
	} );
	
	
	
	
	var _selector_run = function ( type, selector, selectFn, settings, opts )
	{
		var
			out = [], res,
			a, i, ien, j, jen,
			selectorType = typeof selector;
	
		// Can't just check for isArray here, as an API or jQuery instance might be
		// given with their array like look
		if ( ! selector || selectorType === 'string' || selectorType === 'function' || selector.length === undefined ) {
			selector = [ selector ];
		}
	
		for ( i=0, ien=selector.length ; i<ien ; i++ ) {
			// Only split on simple strings - complex expressions will be jQuery selectors
			a = selector[i] && selector[i].split && ! selector[i].match(/[\[\(:]/) ?
				selector[i].split(',') :
				[ selector[i] ];
	
			for ( j=0, jen=a.length ; j<jen ; j++ ) {
				res = selectFn( typeof a[j] === 'string' ? $.trim(a[j]) : a[j] );
	
				if ( res && res.length ) {
					out = out.concat( res );
				}
			}
		}
	
		// selector extensions
		var ext = _ext.selector[ type ];
		if ( ext.length ) {
			for ( i=0, ien=ext.length ; i<ien ; i++ ) {
				out = ext[i]( settings, opts, out );
			}
		}
	
		return _unique( out );
	};
	
	
	var _selector_opts = function ( opts )
	{
		if ( ! opts ) {
			opts = {};
		}
	
		// Backwards compatibility for 1.9- which used the terminology filter rather
		// than search
		if ( opts.filter && opts.search === undefined ) {
			opts.search = opts.filter;
		}
	
		return $.extend( {
			search: 'none',
			order: 'current',
			page: 'all'
		}, opts );
	};
	
	
	var _selector_first = function ( inst )
	{
		// Reduce the API instance to the first item found
		for ( var i=0, ien=inst.length ; i<ien ; i++ ) {
			if ( inst[i].length > 0 ) {
				// Assign the first element to the first item in the instance
				// and truncate the instance and context
				inst[0] = inst[i];
				inst[0].length = 1;
				inst.length = 1;
				inst.context = [ inst.context[i] ];
	
				return inst;
			}
		}
	
		// Not found - return an empty instance
		inst.length = 0;
		return inst;
	};
	
	
	var _selector_row_indexes = function ( settings, opts )
	{
		var
			i, ien, tmp, a=[],
			displayFiltered = settings.aiDisplay,
			displayMaster = settings.aiDisplayMaster;
	
		var
			search = opts.search,  // none, applied, removed
			order  = opts.order,   // applied, current, index (original - compatibility with 1.9)
			page   = opts.page;    // all, current
	
		if ( _fnDataSource( settings ) == 'ssp' ) {
			// In server-side processing mode, most options are irrelevant since
			// rows not shown don't exist and the index order is the applied order
			// Removed is a special case - for consistency just return an empty
			// array
			return search === 'removed' ?
				[] :
				_range( 0, displayMaster.length );
		}
		else if ( page == 'current' ) {
			// Current page implies that order=current and fitler=applied, since it is
			// fairly senseless otherwise, regardless of what order and search actually
			// are
			for ( i=settings._iDisplayStart, ien=settings.fnDisplayEnd() ; i<ien ; i++ ) {
				a.push( displayFiltered[i] );
			}
		}
		else if ( order == 'current' || order == 'applied' ) {
			a = search == 'none' ?
				displayMaster.slice() :                      // no search
				search == 'applied' ?
					displayFiltered.slice() :                // applied search
					$.map( displayMaster, function (el, i) { // removed search
						return $.inArray( el, displayFiltered ) === -1 ? el : null;
					} );
		}
		else if ( order == 'index' || order == 'original' ) {
			for ( i=0, ien=settings.aoData.length ; i<ien ; i++ ) {
				if ( search == 'none' ) {
					a.push( i );
				}
				else { // applied | removed
					tmp = $.inArray( i, displayFiltered );
	
					if ((tmp === -1 && search == 'removed') ||
						(tmp >= 0   && search == 'applied') )
					{
						a.push( i );
					}
				}
			}
		}
	
		return a;
	};
	
	
	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Rows
	 *
	 * {}          - no selector - use all available rows
	 * {integer}   - row aoData index
	 * {node}      - TR node
	 * {string}    - jQuery selector to apply to the TR elements
	 * {array}     - jQuery array of nodes, or simply an array of TR nodes
	 *
	 */
	
	
	var __row_selector = function ( settings, selector, opts )
	{
		var rows;
		var run = function ( sel ) {
			var selInt = _intVal( sel );
			var i, ien;
	
			// Short cut - selector is a number and no options provided (default is
			// all records, so no need to check if the index is in there, since it
			// must be - dev error if the index doesn't exist).
			if ( selInt !== null && ! opts ) {
				return [ selInt ];
			}
	
			if ( ! rows ) {
				rows = _selector_row_indexes( settings, opts );
			}
	
			if ( selInt !== null && $.inArray( selInt, rows ) !== -1 ) {
				// Selector - integer
				return [ selInt ];
			}
			else if ( sel === null || sel === undefined || sel === '' ) {
				// Selector - none
				return rows;
			}
	
			// Selector - function
			if ( typeof sel === 'function' ) {
				return $.map( rows, function (idx) {
					var row = settings.aoData[ idx ];
					return sel( idx, row._aData, row.nTr ) ? idx : null;
				} );
			}
	
			// Get nodes in the order from the `rows` array with null values removed
			var nodes = _removeEmpty(
				_pluck_order( settings.aoData, rows, 'nTr' )
			);
	
			// Selector - node
			if ( sel.nodeName ) {
				if ( sel._DT_RowIndex !== undefined ) {
					return [ sel._DT_RowIndex ]; // Property added by DT for fast lookup
				}
				else if ( sel._DT_CellIndex ) {
					return [ sel._DT_CellIndex.row ];
				}
				else {
					var host = $(sel).closest('*[data-dt-row]');
					return host.length ?
						[ host.data('dt-row') ] :
						[];
				}
			}
	
			// ID selector. Want to always be able to select rows by id, regardless
			// of if the tr element has been created or not, so can't rely upon
			// jQuery here - hence a custom implementation. This does not match
			// Sizzle's fast selector or HTML4 - in HTML5 the ID can be anything,
			// but to select it using a CSS selector engine (like Sizzle or
			// querySelect) it would need to need to be escaped for some characters.
			// DataTables simplifies this for row selectors since you can select
			// only a row. A # indicates an id any anything that follows is the id -
			// unescaped.
			if ( typeof sel === 'string' && sel.charAt(0) === '#' ) {
				// get row index from id
				var rowObj = settings.aIds[ sel.replace( /^#/, '' ) ];
				if ( rowObj !== undefined ) {
					return [ rowObj.idx ];
				}
	
				// need to fall through to jQuery in case there is DOM id that
				// matches
			}
	
			// Selector - jQuery selector string, array of nodes or jQuery object/
			// As jQuery's .filter() allows jQuery objects to be passed in filter,
			// it also allows arrays, so this will cope with all three options
			return $(nodes)
				.filter( sel )
				.map( function () {
					return this._DT_RowIndex;
				} )
				.toArray();
		};
	
		return _selector_run( 'row', selector, run, settings, opts );
	};
	
	
	_api_register( 'rows()', function ( selector, opts ) {
		// argument shifting
		if ( selector === undefined ) {
			selector = '';
		}
		else if ( $.isPlainObject( selector ) ) {
			opts = selector;
			selector = '';
		}
	
		opts = _selector_opts( opts );
	
		var inst = this.iterator( 'table', function ( settings ) {
			return __row_selector( settings, selector, opts );
		}, 1 );
	
		// Want argument shifting here and in __row_selector?
		inst.selector.rows = selector;
		inst.selector.opts = opts;
	
		return inst;
	} );
	
	_api_register( 'rows().nodes()', function () {
		return this.iterator( 'row', function ( settings, row ) {
			return settings.aoData[ row ].nTr || undefined;
		}, 1 );
	} );
	
	_api_register( 'rows().data()', function () {
		return this.iterator( true, 'rows', function ( settings, rows ) {
			return _pluck_order( settings.aoData, rows, '_aData' );
		}, 1 );
	} );
	
	_api_registerPlural( 'rows().cache()', 'row().cache()', function ( type ) {
		return this.iterator( 'row', function ( settings, row ) {
			var r = settings.aoData[ row ];
			return type === 'search' ? r._aFilterData : r._aSortData;
		}, 1 );
	} );
	
	_api_registerPlural( 'rows().invalidate()', 'row().invalidate()', function ( src ) {
		return this.iterator( 'row', function ( settings, row ) {
			_fnInvalidate( settings, row, src );
		} );
	} );
	
	_api_registerPlural( 'rows().indexes()', 'row().index()', function () {
		return this.iterator( 'row', function ( settings, row ) {
			return row;
		}, 1 );
	} );
	
	_api_registerPlural( 'rows().ids()', 'row().id()', function ( hash ) {
		var a = [];
		var context = this.context;
	
		// `iterator` will drop undefined values, but in this case we want them
		for ( var i=0, ien=context.length ; i<ien ; i++ ) {
			for ( var j=0, jen=this[i].length ; j<jen ; j++ ) {
				var id = context[i].rowIdFn( context[i].aoData[ this[i][j] ]._aData );
				a.push( (hash === true ? '#' : '' )+ id );
			}
		}
	
		return new _Api( context, a );
	} );
	
	_api_registerPlural( 'rows().remove()', 'row().remove()', function () {
		var that = this;
	
		this.iterator( 'row', function ( settings, row, thatIdx ) {
			var data = settings.aoData;
			var rowData = data[ row ];
			var i, ien, j, jen;
			var loopRow, loopCells;
	
			data.splice( row, 1 );
	
			// Update the cached indexes
			for ( i=0, ien=data.length ; i<ien ; i++ ) {
				loopRow = data[i];
				loopCells = loopRow.anCells;
	
				// Rows
				if ( loopRow.nTr !== null ) {
					loopRow.nTr._DT_RowIndex = i;
				}
	
				// Cells
				if ( loopCells !== null ) {
					for ( j=0, jen=loopCells.length ; j<jen ; j++ ) {
						loopCells[j]._DT_CellIndex.row = i;
					}
				}
			}
	
			// Delete from the display arrays
			_fnDeleteIndex( settings.aiDisplayMaster, row );
			_fnDeleteIndex( settings.aiDisplay, row );
			_fnDeleteIndex( that[ thatIdx ], row, false ); // maintain local indexes
	
			// For server-side processing tables - subtract the deleted row from the count
			if ( settings._iRecordsDisplay > 0 ) {
				settings._iRecordsDisplay--;
			}
	
			// Check for an 'overflow' they case for displaying the table
			_fnLengthOverflow( settings );
	
			// Remove the row's ID reference if there is one
			var id = settings.rowIdFn( rowData._aData );
			if ( id !== undefined ) {
				delete settings.aIds[ id ];
			}
		} );
	
		this.iterator( 'table', function ( settings ) {
			for ( var i=0, ien=settings.aoData.length ; i<ien ; i++ ) {
				settings.aoData[i].idx = i;
			}
		} );
	
		return this;
	} );
	
	
	_api_register( 'rows.add()', function ( rows ) {
		var newRows = this.iterator( 'table', function ( settings ) {
				var row, i, ien;
				var out = [];
	
				for ( i=0, ien=rows.length ; i<ien ; i++ ) {
					row = rows[i];
	
					if ( row.nodeName && row.nodeName.toUpperCase() === 'TR' ) {
						out.push( _fnAddTr( settings, row )[0] );
					}
					else {
						out.push( _fnAddData( settings, row ) );
					}
				}
	
				return out;
			}, 1 );
	
		// Return an Api.rows() extended instance, so rows().nodes() etc can be used
		var modRows = this.rows( -1 );
		modRows.pop();
		$.merge( modRows, newRows );
	
		return modRows;
	} );
	
	
	
	
	
	/**
	 *
	 */
	_api_register( 'row()', function ( selector, opts ) {
		return _selector_first( this.rows( selector, opts ) );
	} );
	
	
	_api_register( 'row().data()', function ( data ) {
		var ctx = this.context;
	
		if ( data === undefined ) {
			// Get
			return ctx.length && this.length ?
				ctx[0].aoData[ this[0] ]._aData :
				undefined;
		}
	
		// Set
		ctx[0].aoData[ this[0] ]._aData = data;
	
		// Automatically invalidate
		_fnInvalidate( ctx[0], this[0], 'data' );
	
		return this;
	} );
	
	
	_api_register( 'row().node()', function () {
		var ctx = this.context;
	
		return ctx.length && this.length ?
			ctx[0].aoData[ this[0] ].nTr || null :
			null;
	} );
	
	
	_api_register( 'row.add()', function ( row ) {
		// Allow a jQuery object to be passed in - only a single row is added from
		// it though - the first element in the set
		if ( row instanceof $ && row.length ) {
			row = row[0];
		}
	
		var rows = this.iterator( 'table', function ( settings ) {
			if ( row.nodeName && row.nodeName.toUpperCase() === 'TR' ) {
				return _fnAddTr( settings, row )[0];
			}
			return _fnAddData( settings, row );
		} );
	
		// Return an Api.rows() extended instance, with the newly added row selected
		return this.row( rows[0] );
	} );
	
	
	
	var __details_add = function ( ctx, row, data, klass )
	{
		// Convert to array of TR elements
		var rows = [];
		var addRow = function ( r, k ) {
			// Recursion to allow for arrays of jQuery objects
			if ( $.isArray( r ) || r instanceof $ ) {
				for ( var i=0, ien=r.length ; i<ien ; i++ ) {
					addRow( r[i], k );
				}
				return;
			}
	
			// If we get a TR element, then just add it directly - up to the dev
			// to add the correct number of columns etc
			if ( r.nodeName && r.nodeName.toLowerCase() === 'tr' ) {
				rows.push( r );
			}
			else {
				// Otherwise create a row with a wrapper
				var created = $('<tr><td/></tr>').addClass( k );
				$('td', created)
					.addClass( k )
					.html( r )
					[0].colSpan = _fnVisbleColumns( ctx );
	
				rows.push( created[0] );
			}
		};
	
		addRow( data, klass );
	
		if ( row._details ) {
			row._details.detach();
		}
	
		row._details = $(rows);
	
		// If the children were already shown, that state should be retained
		if ( row._detailsShow ) {
			row._details.insertAfter( row.nTr );
		}
	};
	
	
	var __details_remove = function ( api, idx )
	{
		var ctx = api.context;
	
		if ( ctx.length ) {
			var row = ctx[0].aoData[ idx !== undefined ? idx : api[0] ];
	
			if ( row && row._details ) {
				row._details.remove();
	
				row._detailsShow = undefined;
				row._details = undefined;
			}
		}
	};
	
	
	var __details_display = function ( api, show ) {
		var ctx = api.context;
	
		if ( ctx.length && api.length ) {
			var row = ctx[0].aoData[ api[0] ];
	
			if ( row._details ) {
				row._detailsShow = show;
	
				if ( show ) {
					row._details.insertAfter( row.nTr );
				}
				else {
					row._details.detach();
				}
	
				__details_events( ctx[0] );
			}
		}
	};
	
	
	var __details_events = function ( settings )
	{
		var api = new _Api( settings );
		var namespace = '.dt.DT_details';
		var drawEvent = 'draw'+namespace;
		var colvisEvent = 'column-visibility'+namespace;
		var destroyEvent = 'destroy'+namespace;
		var data = settings.aoData;
	
		api.off( drawEvent +' '+ colvisEvent +' '+ destroyEvent );
	
		if ( _pluck( data, '_details' ).length > 0 ) {
			// On each draw, insert the required elements into the document
			api.on( drawEvent, function ( e, ctx ) {
				if ( settings !== ctx ) {
					return;
				}
	
				api.rows( {page:'current'} ).eq(0).each( function (idx) {
					// Internal data grab
					var row = data[ idx ];
	
					if ( row._detailsShow ) {
						row._details.insertAfter( row.nTr );
					}
				} );
			} );
	
			// Column visibility change - update the colspan
			api.on( colvisEvent, function ( e, ctx, idx, vis ) {
				if ( settings !== ctx ) {
					return;
				}
	
				// Update the colspan for the details rows (note, only if it already has
				// a colspan)
				var row, visible = _fnVisbleColumns( ctx );
	
				for ( var i=0, ien=data.length ; i<ien ; i++ ) {
					row = data[i];
	
					if ( row._details ) {
						row._details.children('td[colspan]').attr('colspan', visible );
					}
				}
			} );
	
			// Table destroyed - nuke any child rows
			api.on( destroyEvent, function ( e, ctx ) {
				if ( settings !== ctx ) {
					return;
				}
	
				for ( var i=0, ien=data.length ; i<ien ; i++ ) {
					if ( data[i]._details ) {
						__details_remove( api, i );
					}
				}
			} );
		}
	};
	
	// Strings for the method names to help minification
	var _emp = '';
	var _child_obj = _emp+'row().child';
	var _child_mth = _child_obj+'()';
	
	// data can be:
	//  tr
	//  string
	//  jQuery or array of any of the above
	_api_register( _child_mth, function ( data, klass ) {
		var ctx = this.context;
	
		if ( data === undefined ) {
			// get
			return ctx.length && this.length ?
				ctx[0].aoData[ this[0] ]._details :
				undefined;
		}
		else if ( data === true ) {
			// show
			this.child.show();
		}
		else if ( data === false ) {
			// remove
			__details_remove( this );
		}
		else if ( ctx.length && this.length ) {
			// set
			__details_add( ctx[0], ctx[0].aoData[ this[0] ], data, klass );
		}
	
		return this;
	} );
	
	
	_api_register( [
		_child_obj+'.show()',
		_child_mth+'.show()' // only when `child()` was called with parameters (without
	], function ( show ) {   // it returns an object and this method is not executed)
		__details_display( this, true );
		return this;
	} );
	
	
	_api_register( [
		_child_obj+'.hide()',
		_child_mth+'.hide()' // only when `child()` was called with parameters (without
	], function () {         // it returns an object and this method is not executed)
		__details_display( this, false );
		return this;
	} );
	
	
	_api_register( [
		_child_obj+'.remove()',
		_child_mth+'.remove()' // only when `child()` was called with parameters (without
	], function () {           // it returns an object and this method is not executed)
		__details_remove( this );
		return this;
	} );
	
	
	_api_register( _child_obj+'.isShown()', function () {
		var ctx = this.context;
	
		if ( ctx.length && this.length ) {
			// _detailsShown as false or undefined will fall through to return false
			return ctx[0].aoData[ this[0] ]._detailsShow || false;
		}
		return false;
	} );
	
	
	
	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Columns
	 *
	 * {integer}           - column index (>=0 count from left, <0 count from right)
	 * "{integer}:visIdx"  - visible column index (i.e. translate to column index)  (>=0 count from left, <0 count from right)
	 * "{integer}:visible" - alias for {integer}:visIdx  (>=0 count from left, <0 count from right)
	 * "{string}:name"     - column name
	 * "{string}"          - jQuery selector on column header nodes
	 *
	 */
	
	// can be an array of these items, comma separated list, or an array of comma
	// separated lists
	
	var __re_column_selector = /^([^:]+):(name|visIdx|visible)$/;
	
	
	// r1 and r2 are redundant - but it means that the parameters match for the
	// iterator callback in columns().data()
	var __columnData = function ( settings, column, r1, r2, rows ) {
		var a = [];
		for ( var row=0, ien=rows.length ; row<ien ; row++ ) {
			a.push( _fnGetCellData( settings, rows[row], column ) );
		}
		return a;
	};
	
	
	var __column_selector = function ( settings, selector, opts )
	{
		var
			columns = settings.aoColumns,
			names = _pluck( columns, 'sName' ),
			nodes = _pluck( columns, 'nTh' );
	
		var run = function ( s ) {
			var selInt = _intVal( s );
	
			// Selector - all
			if ( s === '' ) {
				return _range( columns.length );
			}
	
			// Selector - index
			if ( selInt !== null ) {
				return [ selInt >= 0 ?
					selInt : // Count from left
					columns.length + selInt // Count from right (+ because its a negative value)
				];
			}
	
			// Selector = function
			if ( typeof s === 'function' ) {
				var rows = _selector_row_indexes( settings, opts );
	
				return $.map( columns, function (col, idx) {
					return s(
							idx,
							__columnData( settings, idx, 0, 0, rows ),
							nodes[ idx ]
						) ? idx : null;
				} );
			}
	
			// jQuery or string selector
			var match = typeof s === 'string' ?
				s.match( __re_column_selector ) :
				'';
	
			if ( match ) {
				switch( match[2] ) {
					case 'visIdx':
					case 'visible':
						var idx = parseInt( match[1], 10 );
						// Visible index given, convert to column index
						if ( idx < 0 ) {
							// Counting from the right
							var visColumns = $.map( columns, function (col,i) {
								return col.bVisible ? i : null;
							} );
							return [ visColumns[ visColumns.length + idx ] ];
						}
						// Counting from the left
						return [ _fnVisibleToColumnIndex( settings, idx ) ];
	
					case 'name':
						// match by name. `names` is column index complete and in order
						return $.map( names, function (name, i) {
							return name === match[1] ? i : null;
						} );
	
					default:
						return [];
				}
			}
	
			// Cell in the table body
			if ( s.nodeName && s._DT_CellIndex ) {
				return [ s._DT_CellIndex.column ];
			}
	
			// jQuery selector on the TH elements for the columns
			var jqResult = $( nodes )
				.filter( s )
				.map( function () {
					return $.inArray( this, nodes ); // `nodes` is column index complete and in order
				} )
				.toArray();
	
			if ( jqResult.length || ! s.nodeName ) {
				return jqResult;
			}
	
			// Otherwise a node which might have a `dt-column` data attribute, or be
			// a child or such an element
			var host = $(s).closest('*[data-dt-column]');
			return host.length ?
				[ host.data('dt-column') ] :
				[];
		};
	
		return _selector_run( 'column', selector, run, settings, opts );
	};
	
	
	var __setColumnVis = function ( settings, column, vis ) {
		var
			cols = settings.aoColumns,
			col  = cols[ column ],
			data = settings.aoData,
			row, cells, i, ien, tr;
	
		// Get
		if ( vis === undefined ) {
			return col.bVisible;
		}
	
		// Set
		// No change
		if ( col.bVisible === vis ) {
			return;
		}
	
		if ( vis ) {
			// Insert column
			// Need to decide if we should use appendChild or insertBefore
			var insertBefore = $.inArray( true, _pluck(cols, 'bVisible'), column+1 );
	
			for ( i=0, ien=data.length ; i<ien ; i++ ) {
				tr = data[i].nTr;
				cells = data[i].anCells;
	
				if ( tr ) {
					// insertBefore can act like appendChild if 2nd arg is null
					tr.insertBefore( cells[ column ], cells[ insertBefore ] || null );
				}
			}
		}
		else {
			// Remove column
			$( _pluck( settings.aoData, 'anCells', column ) ).detach();
		}
	
		// Common actions
		col.bVisible = vis;
		_fnDrawHead( settings, settings.aoHeader );
		_fnDrawHead( settings, settings.aoFooter );
	
		_fnSaveState( settings );
	};
	
	
	_api_register( 'columns()', function ( selector, opts ) {
		// argument shifting
		if ( selector === undefined ) {
			selector = '';
		}
		else if ( $.isPlainObject( selector ) ) {
			opts = selector;
			selector = '';
		}
	
		opts = _selector_opts( opts );
	
		var inst = this.iterator( 'table', function ( settings ) {
			return __column_selector( settings, selector, opts );
		}, 1 );
	
		// Want argument shifting here and in _row_selector?
		inst.selector.cols = selector;
		inst.selector.opts = opts;
	
		return inst;
	} );
	
	_api_registerPlural( 'columns().header()', 'column().header()', function ( selector, opts ) {
		return this.iterator( 'column', function ( settings, column ) {
			return settings.aoColumns[column].nTh;
		}, 1 );
	} );
	
	_api_registerPlural( 'columns().footer()', 'column().footer()', function ( selector, opts ) {
		return this.iterator( 'column', function ( settings, column ) {
			return settings.aoColumns[column].nTf;
		}, 1 );
	} );
	
	_api_registerPlural( 'columns().data()', 'column().data()', function () {
		return this.iterator( 'column-rows', __columnData, 1 );
	} );
	
	_api_registerPlural( 'columns().dataSrc()', 'column().dataSrc()', function () {
		return this.iterator( 'column', function ( settings, column ) {
			return settings.aoColumns[column].mData;
		}, 1 );
	} );
	
	_api_registerPlural( 'columns().cache()', 'column().cache()', function ( type ) {
		return this.iterator( 'column-rows', function ( settings, column, i, j, rows ) {
			return _pluck_order( settings.aoData, rows,
				type === 'search' ? '_aFilterData' : '_aSortData', column
			);
		}, 1 );
	} );
	
	_api_registerPlural( 'columns().nodes()', 'column().nodes()', function () {
		return this.iterator( 'column-rows', function ( settings, column, i, j, rows ) {
			return _pluck_order( settings.aoData, rows, 'anCells', column ) ;
		}, 1 );
	} );
	
	_api_registerPlural( 'columns().visible()', 'column().visible()', function ( vis, calc ) {
		var ret = this.iterator( 'column', function ( settings, column ) {
			if ( vis === undefined ) {
				return settings.aoColumns[ column ].bVisible;
			} // else
			__setColumnVis( settings, column, vis );
		} );
	
		// Group the column visibility changes
		if ( vis !== undefined ) {
			// Second loop once the first is done for events
			this.iterator( 'column', function ( settings, column ) {
				_fnCallbackFire( settings, null, 'column-visibility', [settings, column, vis, calc] );
			} );
	
			if ( calc === undefined || calc ) {
				this.columns.adjust();
			}
		}
	
		return ret;
	} );
	
	_api_registerPlural( 'columns().indexes()', 'column().index()', function ( type ) {
		return this.iterator( 'column', function ( settings, column ) {
			return type === 'visible' ?
				_fnColumnIndexToVisible( settings, column ) :
				column;
		}, 1 );
	} );
	
	_api_register( 'columns.adjust()', function () {
		return this.iterator( 'table', function ( settings ) {
			_fnAdjustColumnSizing( settings );
		}, 1 );
	} );
	
	_api_register( 'column.index()', function ( type, idx ) {
		if ( this.context.length !== 0 ) {
			var ctx = this.context[0];
	
			if ( type === 'fromVisible' || type === 'toData' ) {
				return _fnVisibleToColumnIndex( ctx, idx );
			}
			else if ( type === 'fromData' || type === 'toVisible' ) {
				return _fnColumnIndexToVisible( ctx, idx );
			}
		}
	} );
	
	_api_register( 'column()', function ( selector, opts ) {
		return _selector_first( this.columns( selector, opts ) );
	} );
	
	
	
	var __cell_selector = function ( settings, selector, opts )
	{
		var data = settings.aoData;
		var rows = _selector_row_indexes( settings, opts );
		var cells = _removeEmpty( _pluck_order( data, rows, 'anCells' ) );
		var allCells = $( [].concat.apply([], cells) );
		var row;
		var columns = settings.aoColumns.length;
		var a, i, ien, j, o, host;
	
		var run = function ( s ) {
			var fnSelector = typeof s === 'function';
	
			if ( s === null || s === undefined || fnSelector ) {
				// All cells and function selectors
				a = [];
	
				for ( i=0, ien=rows.length ; i<ien ; i++ ) {
					row = rows[i];
	
					for ( j=0 ; j<columns ; j++ ) {
						o = {
							row: row,
							column: j
						};
	
						if ( fnSelector ) {
							// Selector - function
							host = data[ row ];
	
							if ( s( o, _fnGetCellData(settings, row, j), host.anCells ? host.anCells[j] : null ) ) {
								a.push( o );
							}
						}
						else {
							// Selector - all
							a.push( o );
						}
					}
				}
	
				return a;
			}
			
			// Selector - index
			if ( $.isPlainObject( s ) ) {
				return [s];
			}
	
			// Selector - jQuery filtered cells
			var jqResult = allCells
				.filter( s )
				.map( function (i, el) {
					return { // use a new object, in case someone changes the values
						row:    el._DT_CellIndex.row,
						column: el._DT_CellIndex.column
	 				};
				} )
				.toArray();
	
			if ( jqResult.length || ! s.nodeName ) {
				return jqResult;
			}
	
			// Otherwise the selector is a node, and there is one last option - the
			// element might be a child of an element which has dt-row and dt-column
			// data attributes
			host = $(s).closest('*[data-dt-row]');
			return host.length ?
				[ {
					row: host.data('dt-row'),
					column: host.data('dt-column')
				} ] :
				[];
		};
	
		return _selector_run( 'cell', selector, run, settings, opts );
	};
	
	
	
	
	_api_register( 'cells()', function ( rowSelector, columnSelector, opts ) {
		// Argument shifting
		if ( $.isPlainObject( rowSelector ) ) {
			// Indexes
			if ( rowSelector.row === undefined ) {
				// Selector options in first parameter
				opts = rowSelector;
				rowSelector = null;
			}
			else {
				// Cell index objects in first parameter
				opts = columnSelector;
				columnSelector = null;
			}
		}
		if ( $.isPlainObject( columnSelector ) ) {
			opts = columnSelector;
			columnSelector = null;
		}
	
		// Cell selector
		if ( columnSelector === null || columnSelector === undefined ) {
			return this.iterator( 'table', function ( settings ) {
				return __cell_selector( settings, rowSelector, _selector_opts( opts ) );
			} );
		}
	
		// Row + column selector
		var columns = this.columns( columnSelector, opts );
		var rows = this.rows( rowSelector, opts );
		var a, i, ien, j, jen;
	
		var cells = this.iterator( 'table', function ( settings, idx ) {
			a = [];
	
			for ( i=0, ien=rows[idx].length ; i<ien ; i++ ) {
				for ( j=0, jen=columns[idx].length ; j<jen ; j++ ) {
					a.push( {
						row:    rows[idx][i],
						column: columns[idx][j]
					} );
				}
			}
	
			return a;
		}, 1 );
	
		$.extend( cells.selector, {
			cols: columnSelector,
			rows: rowSelector,
			opts: opts
		} );
	
		return cells;
	} );
	
	
	_api_registerPlural( 'cells().nodes()', 'cell().node()', function () {
		return this.iterator( 'cell', function ( settings, row, column ) {
			var data = settings.aoData[ row ];
	
			return data && data.anCells ?
				data.anCells[ column ] :
				undefined;
		}, 1 );
	} );
	
	
	_api_register( 'cells().data()', function () {
		return this.iterator( 'cell', function ( settings, row, column ) {
			return _fnGetCellData( settings, row, column );
		}, 1 );
	} );
	
	
	_api_registerPlural( 'cells().cache()', 'cell().cache()', function ( type ) {
		type = type === 'search' ? '_aFilterData' : '_aSortData';
	
		return this.iterator( 'cell', function ( settings, row, column ) {
			return settings.aoData[ row ][ type ][ column ];
		}, 1 );
	} );
	
	
	_api_registerPlural( 'cells().render()', 'cell().render()', function ( type ) {
		return this.iterator( 'cell', function ( settings, row, column ) {
			return _fnGetCellData( settings, row, column, type );
		}, 1 );
	} );
	
	
	_api_registerPlural( 'cells().indexes()', 'cell().index()', function () {
		return this.iterator( 'cell', function ( settings, row, column ) {
			return {
				row: row,
				column: column,
				columnVisible: _fnColumnIndexToVisible( settings, column )
			};
		}, 1 );
	} );
	
	
	_api_registerPlural( 'cells().invalidate()', 'cell().invalidate()', function ( src ) {
		return this.iterator( 'cell', function ( settings, row, column ) {
			_fnInvalidate( settings, row, src, column );
		} );
	} );
	
	
	
	_api_register( 'cell()', function ( rowSelector, columnSelector, opts ) {
		return _selector_first( this.cells( rowSelector, columnSelector, opts ) );
	} );
	
	
	_api_register( 'cell().data()', function ( data ) {
		var ctx = this.context;
		var cell = this[0];
	
		if ( data === undefined ) {
			// Get
			return ctx.length && cell.length ?
				_fnGetCellData( ctx[0], cell[0].row, cell[0].column ) :
				undefined;
		}
	
		// Set
		_fnSetCellData( ctx[0], cell[0].row, cell[0].column, data );
		_fnInvalidate( ctx[0], cell[0].row, 'data', cell[0].column );
	
		return this;
	} );
	
	
	
	/**
	 * Get current ordering (sorting) that has been applied to the table.
	 *
	 * @returns {array} 2D array containing the sorting information for the first
	 *   table in the current context. Each element in the parent array represents
	 *   a column being sorted upon (i.e. multi-sorting with two columns would have
	 *   2 inner arrays). The inner arrays may have 2 or 3 elements. The first is
	 *   the column index that the sorting condition applies to, the second is the
	 *   direction of the sort (`desc` or `asc`) and, optionally, the third is the
	 *   index of the sorting order from the `column.sorting` initialisation array.
	 *//**
	 * Set the ordering for the table.
	 *
	 * @param {integer} order Column index to sort upon.
	 * @param {string} direction Direction of the sort to be applied (`asc` or `desc`)
	 * @returns {DataTables.Api} this
	 *//**
	 * Set the ordering for the table.
	 *
	 * @param {array} order 1D array of sorting information to be applied.
	 * @param {array} [...] Optional additional sorting conditions
	 * @returns {DataTables.Api} this
	 *//**
	 * Set the ordering for the table.
	 *
	 * @param {array} order 2D array of sorting information to be applied.
	 * @returns {DataTables.Api} this
	 */
	_api_register( 'order()', function ( order, dir ) {
		var ctx = this.context;
	
		if ( order === undefined ) {
			// get
			return ctx.length !== 0 ?
				ctx[0].aaSorting :
				undefined;
		}
	
		// set
		if ( typeof order === 'number' ) {
			// Simple column / direction passed in
			order = [ [ order, dir ] ];
		}
		else if ( order.length && ! $.isArray( order[0] ) ) {
			// Arguments passed in (list of 1D arrays)
			order = Array.prototype.slice.call( arguments );
		}
		// otherwise a 2D array was passed in
	
		return this.iterator( 'table', function ( settings ) {
			settings.aaSorting = order.slice();
		} );
	} );
	
	
	/**
	 * Attach a sort listener to an element for a given column
	 *
	 * @param {node|jQuery|string} node Identifier for the element(s) to attach the
	 *   listener to. This can take the form of a single DOM node, a jQuery
	 *   collection of nodes or a jQuery selector which will identify the node(s).
	 * @param {integer} column the column that a click on this node will sort on
	 * @param {function} [callback] callback function when sort is run
	 * @returns {DataTables.Api} this
	 */
	_api_register( 'order.listener()', function ( node, column, callback ) {
		return this.iterator( 'table', function ( settings ) {
			_fnSortAttachListener( settings, node, column, callback );
		} );
	} );
	
	
	_api_register( 'order.fixed()', function ( set ) {
		if ( ! set ) {
			var ctx = this.context;
			var fixed = ctx.length ?
				ctx[0].aaSortingFixed :
				undefined;
	
			return $.isArray( fixed ) ?
				{ pre: fixed } :
				fixed;
		}
	
		return this.iterator( 'table', function ( settings ) {
			settings.aaSortingFixed = $.extend( true, {}, set );
		} );
	} );
	
	
	// Order by the selected column(s)
	_api_register( [
		'columns().order()',
		'column().order()'
	], function ( dir ) {
		var that = this;
	
		return this.iterator( 'table', function ( settings, i ) {
			var sort = [];
	
			$.each( that[i], function (j, col) {
				sort.push( [ col, dir ] );
			} );
	
			settings.aaSorting = sort;
		} );
	} );
	
	
	
	_api_register( 'search()', function ( input, regex, smart, caseInsen ) {
		var ctx = this.context;
	
		if ( input === undefined ) {
			// get
			return ctx.length !== 0 ?
				ctx[0].oPreviousSearch.sSearch :
				undefined;
		}
	
		// set
		return this.iterator( 'table', function ( settings ) {
			if ( ! settings.oFeatures.bFilter ) {
				return;
			}
	
			_fnFilterComplete( settings, $.extend( {}, settings.oPreviousSearch, {
				"sSearch": input+"",
				"bRegex":  regex === null ? false : regex,
				"bSmart":  smart === null ? true  : smart,
				"bCaseInsensitive": caseInsen === null ? true : caseInsen
			} ), 1 );
		} );
	} );
	
	
	_api_registerPlural(
		'columns().search()',
		'column().search()',
		function ( input, regex, smart, caseInsen ) {
			return this.iterator( 'column', function ( settings, column ) {
				var preSearch = settings.aoPreSearchCols;
	
				if ( input === undefined ) {
					// get
					return preSearch[ column ].sSearch;
				}
	
				// set
				if ( ! settings.oFeatures.bFilter ) {
					return;
				}
	
				$.extend( preSearch[ column ], {
					"sSearch": input+"",
					"bRegex":  regex === null ? false : regex,
					"bSmart":  smart === null ? true  : smart,
					"bCaseInsensitive": caseInsen === null ? true : caseInsen
				} );
	
				_fnFilterComplete( settings, settings.oPreviousSearch, 1 );
			} );
		}
	);
	
	/*
	 * State API methods
	 */
	
	_api_register( 'state()', function () {
		return this.context.length ?
			this.context[0].oSavedState :
			null;
	} );
	
	
	_api_register( 'state.clear()', function () {
		return this.iterator( 'table', function ( settings ) {
			// Save an empty object
			settings.fnStateSaveCallback.call( settings.oInstance, settings, {} );
		} );
	} );
	
	
	_api_register( 'state.loaded()', function () {
		return this.context.length ?
			this.context[0].oLoadedState :
			null;
	} );
	
	
	_api_register( 'state.save()', function () {
		return this.iterator( 'table', function ( settings ) {
			_fnSaveState( settings );
		} );
	} );
	
	
	
	/**
	 * Provide a common method for plug-ins to check the version of DataTables being
	 * used, in order to ensure compatibility.
	 *
	 *  @param {string} version Version string to check for, in the format "X.Y.Z".
	 *    Note that the formats "X" and "X.Y" are also acceptable.
	 *  @returns {boolean} true if this version of DataTables is greater or equal to
	 *    the required version, or false if this version of DataTales is not
	 *    suitable
	 *  @static
	 *  @dtopt API-Static
	 *
	 *  @example
	 *    alert( $.fn.dataTable.versionCheck( '1.9.0' ) );
	 */
	DataTable.versionCheck = DataTable.fnVersionCheck = function( version )
	{
		var aThis = DataTable.version.split('.');
		var aThat = version.split('.');
		var iThis, iThat;
	
		for ( var i=0, iLen=aThat.length ; i<iLen ; i++ ) {
			iThis = parseInt( aThis[i], 10 ) || 0;
			iThat = parseInt( aThat[i], 10 ) || 0;
	
			// Parts are the same, keep comparing
			if (iThis === iThat) {
				continue;
			}
	
			// Parts are different, return immediately
			return iThis > iThat;
		}
	
		return true;
	};
	
	
	/**
	 * Check if a `<table>` node is a DataTable table already or not.
	 *
	 *  @param {node|jquery|string} table Table node, jQuery object or jQuery
	 *      selector for the table to test. Note that if more than more than one
	 *      table is passed on, only the first will be checked
	 *  @returns {boolean} true the table given is a DataTable, or false otherwise
	 *  @static
	 *  @dtopt API-Static
	 *
	 *  @example
	 *    if ( ! $.fn.DataTable.isDataTable( '#example' ) ) {
	 *      $('#example').dataTable();
	 *    }
	 */
	DataTable.isDataTable = DataTable.fnIsDataTable = function ( table )
	{
		var t = $(table).get(0);
		var is = false;
	
		if ( table instanceof DataTable.Api ) {
			return true;
		}
	
		$.each( DataTable.settings, function (i, o) {
			var head = o.nScrollHead ? $('table', o.nScrollHead)[0] : null;
			var foot = o.nScrollFoot ? $('table', o.nScrollFoot)[0] : null;
	
			if ( o.nTable === t || head === t || foot === t ) {
				is = true;
			}
		} );
	
		return is;
	};
	
	
	/**
	 * Get all DataTable tables that have been initialised - optionally you can
	 * select to get only currently visible tables.
	 *
	 *  @param {boolean} [visible=false] Flag to indicate if you want all (default)
	 *    or visible tables only.
	 *  @returns {array} Array of `table` nodes (not DataTable instances) which are
	 *    DataTables
	 *  @static
	 *  @dtopt API-Static
	 *
	 *  @example
	 *    $.each( $.fn.dataTable.tables(true), function () {
	 *      $(table).DataTable().columns.adjust();
	 *    } );
	 */
	DataTable.tables = DataTable.fnTables = function ( visible )
	{
		var api = false;
	
		if ( $.isPlainObject( visible ) ) {
			api = visible.api;
			visible = visible.visible;
		}
	
		var a = $.map( DataTable.settings, function (o) {
			if ( !visible || (visible && $(o.nTable).is(':visible')) ) {
				return o.nTable;
			}
		} );
	
		return api ?
			new _Api( a ) :
			a;
	};
	
	
	/**
	 * Convert from camel case parameters to Hungarian notation. This is made public
	 * for the extensions to provide the same ability as DataTables core to accept
	 * either the 1.9 style Hungarian notation, or the 1.10+ style camelCase
	 * parameters.
	 *
	 *  @param {object} src The model object which holds all parameters that can be
	 *    mapped.
	 *  @param {object} user The object to convert from camel case to Hungarian.
	 *  @param {boolean} force When set to `true`, properties which already have a
	 *    Hungarian value in the `user` object will be overwritten. Otherwise they
	 *    won't be.
	 */
	DataTable.camelToHungarian = _fnCamelToHungarian;
	
	
	
	/**
	 *
	 */
	_api_register( '$()', function ( selector, opts ) {
		var
			rows   = this.rows( opts ).nodes(), // Get all rows
			jqRows = $(rows);
	
		return $( [].concat(
			jqRows.filter( selector ).toArray(),
			jqRows.find( selector ).toArray()
		) );
	} );
	
	
	// jQuery functions to operate on the tables
	$.each( [ 'on', 'one', 'off' ], function (i, key) {
		_api_register( key+'()', function ( /* event, handler */ ) {
			var args = Array.prototype.slice.call(arguments);
	
			// Add the `dt` namespace automatically if it isn't already present
			args[0] = $.map( args[0].split( /\s/ ), function ( e ) {
				return ! e.match(/\.dt\b/) ?
					e+'.dt' :
					e;
				} ).join( ' ' );
	
			var inst = $( this.tables().nodes() );
			inst[key].apply( inst, args );
			return this;
		} );
	} );
	
	
	_api_register( 'clear()', function () {
		return this.iterator( 'table', function ( settings ) {
			_fnClearTable( settings );
		} );
	} );
	
	
	_api_register( 'settings()', function () {
		return new _Api( this.context, this.context );
	} );
	
	
	_api_register( 'init()', function () {
		var ctx = this.context;
		return ctx.length ? ctx[0].oInit : null;
	} );
	
	
	_api_register( 'data()', function () {
		return this.iterator( 'table', function ( settings ) {
			return _pluck( settings.aoData, '_aData' );
		} ).flatten();
	} );
	
	
	_api_register( 'destroy()', function ( remove ) {
		remove = remove || false;
	
		return this.iterator( 'table', function ( settings ) {
			var orig      = settings.nTableWrapper.parentNode;
			var classes   = settings.oClasses;
			var table     = settings.nTable;
			var tbody     = settings.nTBody;
			var thead     = settings.nTHead;
			var tfoot     = settings.nTFoot;
			var jqTable   = $(table);
			var jqTbody   = $(tbody);
			var jqWrapper = $(settings.nTableWrapper);
			var rows      = $.map( settings.aoData, function (r) { return r.nTr; } );
			var i, ien;
	
			// Flag to note that the table is currently being destroyed - no action
			// should be taken
			settings.bDestroying = true;
	
			// Fire off the destroy callbacks for plug-ins etc
			_fnCallbackFire( settings, "aoDestroyCallback", "destroy", [settings] );
	
			// If not being removed from the document, make all columns visible
			if ( ! remove ) {
				new _Api( settings ).columns().visible( true );
			}
	
			// Blitz all `DT` namespaced events (these are internal events, the
			// lowercase, `dt` events are user subscribed and they are responsible
			// for removing them
			jqWrapper.off('.DT').find(':not(tbody *)').off('.DT');
			$(window).off('.DT-'+settings.sInstance);
	
			// When scrolling we had to break the table up - restore it
			if ( table != thead.parentNode ) {
				jqTable.children('thead').detach();
				jqTable.append( thead );
			}
	
			if ( tfoot && table != tfoot.parentNode ) {
				jqTable.children('tfoot').detach();
				jqTable.append( tfoot );
			}
	
			settings.aaSorting = [];
			settings.aaSortingFixed = [];
			_fnSortingClasses( settings );
	
			$( rows ).removeClass( settings.asStripeClasses.join(' ') );
	
			$('th, td', thead).removeClass( classes.sSortable+' '+
				classes.sSortableAsc+' '+classes.sSortableDesc+' '+classes.sSortableNone
			);
	
			// Add the TR elements back into the table in their original order
			jqTbody.children().detach();
			jqTbody.append( rows );
	
			// Remove the DataTables generated nodes, events and classes
			var removedMethod = remove ? 'remove' : 'detach';
			jqTable[ removedMethod ]();
			jqWrapper[ removedMethod ]();
	
			// If we need to reattach the table to the document
			if ( ! remove && orig ) {
				// insertBefore acts like appendChild if !arg[1]
				orig.insertBefore( table, settings.nTableReinsertBefore );
	
				// Restore the width of the original table - was read from the style property,
				// so we can restore directly to that
				jqTable
					.css( 'width', settings.sDestroyWidth )
					.removeClass( classes.sTable );
	
				// If the were originally stripe classes - then we add them back here.
				// Note this is not fool proof (for example if not all rows had stripe
				// classes - but it's a good effort without getting carried away
				ien = settings.asDestroyStripes.length;
	
				if ( ien ) {
					jqTbody.children().each( function (i) {
						$(this).addClass( settings.asDestroyStripes[i % ien] );
					} );
				}
			}
	
			/* Remove the settings object from the settings array */
			var idx = $.inArray( settings, DataTable.settings );
			if ( idx !== -1 ) {
				DataTable.settings.splice( idx, 1 );
			}
		} );
	} );
	
	
	// Add the `every()` method for rows, columns and cells in a compact form
	$.each( [ 'column', 'row', 'cell' ], function ( i, type ) {
		_api_register( type+'s().every()', function ( fn ) {
			var opts = this.selector.opts;
			var api = this;
	
			return this.iterator( type, function ( settings, arg1, arg2, arg3, arg4 ) {
				// Rows and columns:
				//  arg1 - index
				//  arg2 - table counter
				//  arg3 - loop counter
				//  arg4 - undefined
				// Cells:
				//  arg1 - row index
				//  arg2 - column index
				//  arg3 - table counter
				//  arg4 - loop counter
				fn.call(
					api[ type ](
						arg1,
						type==='cell' ? arg2 : opts,
						type==='cell' ? opts : undefined
					),
					arg1, arg2, arg3, arg4
				);
			} );
		} );
	} );
	
	
	// i18n method for extensions to be able to use the language object from the
	// DataTable
	_api_register( 'i18n()', function ( token, def, plural ) {
		var ctx = this.context[0];
		var resolved = _fnGetObjectDataFn( token )( ctx.oLanguage );
	
		if ( resolved === undefined ) {
			resolved = def;
		}
	
		if ( plural !== undefined && $.isPlainObject( resolved ) ) {
			resolved = resolved[ plural ] !== undefined ?
				resolved[ plural ] :
				resolved._;
		}
	
		return resolved.replace( '%d', plural ); // nb: plural might be undefined,
	} );

	/**
	 * Version string for plug-ins to check compatibility. Allowed format is
	 * `a.b.c-d` where: a:int, b:int, c:int, d:string(dev|beta|alpha). `d` is used
	 * only for non-release builds. See http://semver.org/ for more information.
	 *  @member
	 *  @type string
	 *  @default Version number
	 */
	DataTable.version = "1.10.16";

	/**
	 * Private data store, containing all of the settings objects that are
	 * created for the tables on a given page.
	 *
	 * Note that the `DataTable.settings` object is aliased to
	 * `jQuery.fn.dataTableExt` through which it may be accessed and
	 * manipulated, or `jQuery.fn.dataTable.settings`.
	 *  @member
	 *  @type array
	 *  @default []
	 *  @private
	 */
	DataTable.settings = [];

	/**
	 * Object models container, for the various models that DataTables has
	 * available to it. These models define the objects that are used to hold
	 * the active state and configuration of the table.
	 *  @namespace
	 */
	DataTable.models = {};
	
	
	
	/**
	 * Template object for the way in which DataTables holds information about
	 * search information for the global filter and individual column filters.
	 *  @namespace
	 */
	DataTable.models.oSearch = {
		/**
		 * Flag to indicate if the filtering should be case insensitive or not
		 *  @type boolean
		 *  @default true
		 */
		"bCaseInsensitive": true,
	
		/**
		 * Applied search term
		 *  @type string
		 *  @default <i>Empty string</i>
		 */
		"sSearch": "",
	
		/**
		 * Flag to indicate if the search term should be interpreted as a
		 * regular expression (true) or not (false) and therefore and special
		 * regex characters escaped.
		 *  @type boolean
		 *  @default false
		 */
		"bRegex": false,
	
		/**
		 * Flag to indicate if DataTables is to use its smart filtering or not.
		 *  @type boolean
		 *  @default true
		 */
		"bSmart": true
	};
	
	
	
	
	/**
	 * Template object for the way in which DataTables holds information about
	 * each individual row. This is the object format used for the settings
	 * aoData array.
	 *  @namespace
	 */
	DataTable.models.oRow = {
		/**
		 * TR element for the row
		 *  @type node
		 *  @default null
		 */
		"nTr": null,
	
		/**
		 * Array of TD elements for each row. This is null until the row has been
		 * created.
		 *  @type array nodes
		 *  @default []
		 */
		"anCells": null,
	
		/**
		 * Data object from the original data source for the row. This is either
		 * an array if using the traditional form of DataTables, or an object if
		 * using mData options. The exact type will depend on the passed in
		 * data from the data source, or will be an array if using DOM a data
		 * source.
		 *  @type array|object
		 *  @default []
		 */
		"_aData": [],
	
		/**
		 * Sorting data cache - this array is ostensibly the same length as the
		 * number of columns (although each index is generated only as it is
		 * needed), and holds the data that is used for sorting each column in the
		 * row. We do this cache generation at the start of the sort in order that
		 * the formatting of the sort data need be done only once for each cell
		 * per sort. This array should not be read from or written to by anything
		 * other than the master sorting methods.
		 *  @type array
		 *  @default null
		 *  @private
		 */
		"_aSortData": null,
	
		/**
		 * Per cell filtering data cache. As per the sort data cache, used to
		 * increase the performance of the filtering in DataTables
		 *  @type array
		 *  @default null
		 *  @private
		 */
		"_aFilterData": null,
	
		/**
		 * Filtering data cache. This is the same as the cell filtering cache, but
		 * in this case a string rather than an array. This is easily computed with
		 * a join on `_aFilterData`, but is provided as a cache so the join isn't
		 * needed on every search (memory traded for performance)
		 *  @type array
		 *  @default null
		 *  @private
		 */
		"_sFilterRow": null,
	
		/**
		 * Cache of the class name that DataTables has applied to the row, so we
		 * can quickly look at this variable rather than needing to do a DOM check
		 * on className for the nTr property.
		 *  @type string
		 *  @default <i>Empty string</i>
		 *  @private
		 */
		"_sRowStripe": "",
	
		/**
		 * Denote if the original data source was from the DOM, or the data source
		 * object. This is used for invalidating data, so DataTables can
		 * automatically read data from the original source, unless uninstructed
		 * otherwise.
		 *  @type string
		 *  @default null
		 *  @private
		 */
		"src": null,
	
		/**
		 * Index in the aoData array. This saves an indexOf lookup when we have the
		 * object, but want to know the index
		 *  @type integer
		 *  @default -1
		 *  @private
		 */
		"idx": -1
	};
	
	
	/**
	 * Template object for the column information object in DataTables. This object
	 * is held in the settings aoColumns array and contains all the information that
	 * DataTables needs about each individual column.
	 *
	 * Note that this object is related to {@link DataTable.defaults.column}
	 * but this one is the internal data store for DataTables's cache of columns.
	 * It should NOT be manipulated outside of DataTables. Any configuration should
	 * be done through the initialisation options.
	 *  @namespace
	 */
	DataTable.models.oColumn = {
		/**
		 * Column index. This could be worked out on-the-fly with $.inArray, but it
		 * is faster to just hold it as a variable
		 *  @type integer
		 *  @default null
		 */
		"idx": null,
	
		/**
		 * A list of the columns that sorting should occur on when this column
		 * is sorted. That this property is an array allows multi-column sorting
		 * to be defined for a column (for example first name / last name columns
		 * would benefit from this). The values are integers pointing to the
		 * columns to be sorted on (typically it will be a single integer pointing
		 * at itself, but that doesn't need to be the case).
		 *  @type array
		 */
		"aDataSort": null,
	
		/**
		 * Define the sorting directions that are applied to the column, in sequence
		 * as the column is repeatedly sorted upon - i.e. the first value is used
		 * as the sorting direction when the column if first sorted (clicked on).
		 * Sort it again (click again) and it will move on to the next index.
		 * Repeat until loop.
		 *  @type array
		 */
		"asSorting": null,
	
		/**
		 * Flag to indicate if the column is searchable, and thus should be included
		 * in the filtering or not.
		 *  @type boolean
		 */
		"bSearchable": null,
	
		/**
		 * Flag to indicate if the column is sortable or not.
		 *  @type boolean
		 */
		"bSortable": null,
	
		/**
		 * Flag to indicate if the column is currently visible in the table or not
		 *  @type boolean
		 */
		"bVisible": null,
	
		/**
		 * Store for manual type assignment using the `column.type` option. This
		 * is held in store so we can manipulate the column's `sType` property.
		 *  @type string
		 *  @default null
		 *  @private
		 */
		"_sManualType": null,
	
		/**
		 * Flag to indicate if HTML5 data attributes should be used as the data
		 * source for filtering or sorting. True is either are.
		 *  @type boolean
		 *  @default false
		 *  @private
		 */
		"_bAttrSrc": false,
	
		/**
		 * Developer definable function that is called whenever a cell is created (Ajax source,
		 * etc) or processed for input (DOM source). This can be used as a compliment to mRender
		 * allowing you to modify the DOM element (add background colour for example) when the
		 * element is available.
		 *  @type function
		 *  @param {element} nTd The TD node that has been created
		 *  @param {*} sData The Data for the cell
		 *  @param {array|object} oData The data for the whole row
		 *  @param {int} iRow The row index for the aoData data store
		 *  @default null
		 */
		"fnCreatedCell": null,
	
		/**
		 * Function to get data from a cell in a column. You should <b>never</b>
		 * access data directly through _aData internally in DataTables - always use
		 * the method attached to this property. It allows mData to function as
		 * required. This function is automatically assigned by the column
		 * initialisation method
		 *  @type function
		 *  @param {array|object} oData The data array/object for the array
		 *    (i.e. aoData[]._aData)
		 *  @param {string} sSpecific The specific data type you want to get -
		 *    'display', 'type' 'filter' 'sort'
		 *  @returns {*} The data for the cell from the given row's data
		 *  @default null
		 */
		"fnGetData": null,
	
		/**
		 * Function to set data for a cell in the column. You should <b>never</b>
		 * set the data directly to _aData internally in DataTables - always use
		 * this method. It allows mData to function as required. This function
		 * is automatically assigned by the column initialisation method
		 *  @type function
		 *  @param {array|object} oData The data array/object for the array
		 *    (i.e. aoData[]._aData)
		 *  @param {*} sValue Value to set
		 *  @default null
		 */
		"fnSetData": null,
	
		/**
		 * Property to read the value for the cells in the column from the data
		 * source array / object. If null, then the default content is used, if a
		 * function is given then the return from the function is used.
		 *  @type function|int|string|null
		 *  @default null
		 */
		"mData": null,
	
		/**
		 * Partner property to mData which is used (only when defined) to get
		 * the data - i.e. it is basically the same as mData, but without the
		 * 'set' option, and also the data fed to it is the result from mData.
		 * This is the rendering method to match the data method of mData.
		 *  @type function|int|string|null
		 *  @default null
		 */
		"mRender": null,
	
		/**
		 * Unique header TH/TD element for this column - this is what the sorting
		 * listener is attached to (if sorting is enabled.)
		 *  @type node
		 *  @default null
		 */
		"nTh": null,
	
		/**
		 * Unique footer TH/TD element for this column (if there is one). Not used
		 * in DataTables as such, but can be used for plug-ins to reference the
		 * footer for each column.
		 *  @type node
		 *  @default null
		 */
		"nTf": null,
	
		/**
		 * The class to apply to all TD elements in the table's TBODY for the column
		 *  @type string
		 *  @default null
		 */
		"sClass": null,
	
		/**
		 * When DataTables calculates the column widths to assign to each column,
		 * it finds the longest string in each column and then constructs a
		 * temporary table and reads the widths from that. The problem with this
		 * is that "mmm" is much wider then "iiii", but the latter is a longer
		 * string - thus the calculation can go wrong (doing it properly and putting
		 * it into an DOM object and measuring that is horribly(!) slow). Thus as
		 * a "work around" we provide this option. It will append its value to the
		 * text that is found to be the longest string for the column - i.e. padding.
		 *  @type string
		 */
		"sContentPadding": null,
	
		/**
		 * Allows a default value to be given for a column's data, and will be used
		 * whenever a null data source is encountered (this can be because mData
		 * is set to null, or because the data source itself is null).
		 *  @type string
		 *  @default null
		 */
		"sDefaultContent": null,
	
		/**
		 * Name for the column, allowing reference to the column by name as well as
		 * by index (needs a lookup to work by name).
		 *  @type string
		 */
		"sName": null,
	
		/**
		 * Custom sorting data type - defines which of the available plug-ins in
		 * afnSortData the custom sorting will use - if any is defined.
		 *  @type string
		 *  @default std
		 */
		"sSortDataType": 'std',
	
		/**
		 * Class to be applied to the header element when sorting on this column
		 *  @type string
		 *  @default null
		 */
		"sSortingClass": null,
	
		/**
		 * Class to be applied to the header element when sorting on this column -
		 * when jQuery UI theming is used.
		 *  @type string
		 *  @default null
		 */
		"sSortingClassJUI": null,
	
		/**
		 * Title of the column - what is seen in the TH element (nTh).
		 *  @type string
		 */
		"sTitle": null,
	
		/**
		 * Column sorting and filtering type
		 *  @type string
		 *  @default null
		 */
		"sType": null,
	
		/**
		 * Width of the column
		 *  @type string
		 *  @default null
		 */
		"sWidth": null,
	
		/**
		 * Width of the column when it was first "encountered"
		 *  @type string
		 *  @default null
		 */
		"sWidthOrig": null
	};
	
	
	/*
	 * Developer note: The properties of the object below are given in Hungarian
	 * notation, that was used as the interface for DataTables prior to v1.10, however
	 * from v1.10 onwards the primary interface is camel case. In order to avoid
	 * breaking backwards compatibility utterly with this change, the Hungarian
	 * version is still, internally the primary interface, but is is not documented
	 * - hence the @name tags in each doc comment. This allows a Javascript function
	 * to create a map from Hungarian notation to camel case (going the other direction
	 * would require each property to be listed, which would at around 3K to the size
	 * of DataTables, while this method is about a 0.5K hit.
	 *
	 * Ultimately this does pave the way for Hungarian notation to be dropped
	 * completely, but that is a massive amount of work and will break current
	 * installs (therefore is on-hold until v2).
	 */
	
	/**
	 * Initialisation options that can be given to DataTables at initialisation
	 * time.
	 *  @namespace
	 */
	DataTable.defaults = {
		/**
		 * An array of data to use for the table, passed in at initialisation which
		 * will be used in preference to any data which is already in the DOM. This is
		 * particularly useful for constructing tables purely in Javascript, for
		 * example with a custom Ajax call.
		 *  @type array
		 *  @default null
		 *
		 *  @dtopt Option
		 *  @name DataTable.defaults.data
		 *
		 *  @example
		 *    // Using a 2D array data source
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "data": [
		 *          ['Trident', 'Internet Explorer 4.0', 'Win 95+', 4, 'X'],
		 *          ['Trident', 'Internet Explorer 5.0', 'Win 95+', 5, 'C'],
		 *        ],
		 *        "columns": [
		 *          { "title": "Engine" },
		 *          { "title": "Browser" },
		 *          { "title": "Platform" },
		 *          { "title": "Version" },
		 *          { "title": "Grade" }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using an array of objects as a data source (`data`)
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "data": [
		 *          {
		 *            "engine":   "Trident",
		 *            "browser":  "Internet Explorer 4.0",
		 *            "platform": "Win 95+",
		 *            "version":  4,
		 *            "grade":    "X"
		 *          },
		 *          {
		 *            "engine":   "Trident",
		 *            "browser":  "Internet Explorer 5.0",
		 *            "platform": "Win 95+",
		 *            "version":  5,
		 *            "grade":    "C"
		 *          }
		 *        ],
		 *        "columns": [
		 *          { "title": "Engine",   "data": "engine" },
		 *          { "title": "Browser",  "data": "browser" },
		 *          { "title": "Platform", "data": "platform" },
		 *          { "title": "Version",  "data": "version" },
		 *          { "title": "Grade",    "data": "grade" }
		 *        ]
		 *      } );
		 *    } );
		 */
		"aaData": null,
	
	
		/**
		 * If ordering is enabled, then DataTables will perform a first pass sort on
		 * initialisation. You can define which column(s) the sort is performed
		 * upon, and the sorting direction, with this variable. The `sorting` array
		 * should contain an array for each column to be sorted initially containing
		 * the column's index and a direction string ('asc' or 'desc').
		 *  @type array
		 *  @default [[0,'asc']]
		 *
		 *  @dtopt Option
		 *  @name DataTable.defaults.order
		 *
		 *  @example
		 *    // Sort by 3rd column first, and then 4th column
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "order": [[2,'asc'], [3,'desc']]
		 *      } );
		 *    } );
		 *
		 *    // No initial sorting
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "order": []
		 *      } );
		 *    } );
		 */
		"aaSorting": [[0,'asc']],
	
	
		/**
		 * This parameter is basically identical to the `sorting` parameter, but
		 * cannot be overridden by user interaction with the table. What this means
		 * is that you could have a column (visible or hidden) which the sorting
		 * will always be forced on first - any sorting after that (from the user)
		 * will then be performed as required. This can be useful for grouping rows
		 * together.
		 *  @type array
		 *  @default null
		 *
		 *  @dtopt Option
		 *  @name DataTable.defaults.orderFixed
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "orderFixed": [[0,'asc']]
		 *      } );
		 *    } )
		 */
		"aaSortingFixed": [],
	
	
		/**
		 * DataTables can be instructed to load data to display in the table from a
		 * Ajax source. This option defines how that Ajax call is made and where to.
		 *
		 * The `ajax` property has three different modes of operation, depending on
		 * how it is defined. These are:
		 *
		 * * `string` - Set the URL from where the data should be loaded from.
		 * * `object` - Define properties for `jQuery.ajax`.
		 * * `function` - Custom data get function
		 *
		 * `string`
		 * --------
		 *
		 * As a string, the `ajax` property simply defines the URL from which
		 * DataTables will load data.
		 *
		 * `object`
		 * --------
		 *
		 * As an object, the parameters in the object are passed to
		 * [jQuery.ajax](http://api.jquery.com/jQuery.ajax/) allowing fine control
		 * of the Ajax request. DataTables has a number of default parameters which
		 * you can override using this option. Please refer to the jQuery
		 * documentation for a full description of the options available, although
		 * the following parameters provide additional options in DataTables or
		 * require special consideration:
		 *
		 * * `data` - As with jQuery, `data` can be provided as an object, but it
		 *   can also be used as a function to manipulate the data DataTables sends
		 *   to the server. The function takes a single parameter, an object of
		 *   parameters with the values that DataTables has readied for sending. An
		 *   object may be returned which will be merged into the DataTables
		 *   defaults, or you can add the items to the object that was passed in and
		 *   not return anything from the function. This supersedes `fnServerParams`
		 *   from DataTables 1.9-.
		 *
		 * * `dataSrc` - By default DataTables will look for the property `data` (or
		 *   `aaData` for compatibility with DataTables 1.9-) when obtaining data
		 *   from an Ajax source or for server-side processing - this parameter
		 *   allows that property to be changed. You can use Javascript dotted
		 *   object notation to get a data source for multiple levels of nesting, or
		 *   it my be used as a function. As a function it takes a single parameter,
		 *   the JSON returned from the server, which can be manipulated as
		 *   required, with the returned value being that used by DataTables as the
		 *   data source for the table. This supersedes `sAjaxDataProp` from
		 *   DataTables 1.9-.
		 *
		 * * `success` - Should not be overridden it is used internally in
		 *   DataTables. To manipulate / transform the data returned by the server
		 *   use `ajax.dataSrc`, or use `ajax` as a function (see below).
		 *
		 * `function`
		 * ----------
		 *
		 * As a function, making the Ajax call is left up to yourself allowing
		 * complete control of the Ajax request. Indeed, if desired, a method other
		 * than Ajax could be used to obtain the required data, such as Web storage
		 * or an AIR database.
		 *
		 * The function is given four parameters and no return is required. The
		 * parameters are:
		 *
		 * 1. _object_ - Data to send to the server
		 * 2. _function_ - Callback function that must be executed when the required
		 *    data has been obtained. That data should be passed into the callback
		 *    as the only parameter
		 * 3. _object_ - DataTables settings object for the table
		 *
		 * Note that this supersedes `fnServerData` from DataTables 1.9-.
		 *
		 *  @type string|object|function
		 *  @default null
		 *
		 *  @dtopt Option
		 *  @name DataTable.defaults.ajax
		 *  @since 1.10.0
		 *
		 * @example
		 *   // Get JSON data from a file via Ajax.
		 *   // Note DataTables expects data in the form `{ data: [ ...data... ] }` by default).
		 *   $('#example').dataTable( {
		 *     "ajax": "data.json"
		 *   } );
		 *
		 * @example
		 *   // Get JSON data from a file via Ajax, using `dataSrc` to change
		 *   // `data` to `tableData` (i.e. `{ tableData: [ ...data... ] }`)
		 *   $('#example').dataTable( {
		 *     "ajax": {
		 *       "url": "data.json",
		 *       "dataSrc": "tableData"
		 *     }
		 *   } );
		 *
		 * @example
		 *   // Get JSON data from a file via Ajax, using `dataSrc` to read data
		 *   // from a plain array rather than an array in an object
		 *   $('#example').dataTable( {
		 *     "ajax": {
		 *       "url": "data.json",
		 *       "dataSrc": ""
		 *     }
		 *   } );
		 *
		 * @example
		 *   // Manipulate the data returned from the server - add a link to data
		 *   // (note this can, should, be done using `render` for the column - this
		 *   // is just a simple example of how the data can be manipulated).
		 *   $('#example').dataTable( {
		 *     "ajax": {
		 *       "url": "data.json",
		 *       "dataSrc": function ( json ) {
		 *         for ( var i=0, ien=json.length ; i<ien ; i++ ) {
		 *           json[i][0] = '<a href="/message/'+json[i][0]+'>View message</a>';
		 *         }
		 *         return json;
		 *       }
		 *     }
		 *   } );
		 *
		 * @example
		 *   // Add data to the request
		 *   $('#example').dataTable( {
		 *     "ajax": {
		 *       "url": "data.json",
		 *       "data": function ( d ) {
		 *         return {
		 *           "extra_search": $('#extra').val()
		 *         };
		 *       }
		 *     }
		 *   } );
		 *
		 * @example
		 *   // Send request as POST
		 *   $('#example').dataTable( {
		 *     "ajax": {
		 *       "url": "data.json",
		 *       "type": "POST"
		 *     }
		 *   } );
		 *
		 * @example
		 *   // Get the data from localStorage (could interface with a form for
		 *   // adding, editing and removing rows).
		 *   $('#example').dataTable( {
		 *     "ajax": function (data, callback, settings) {
		 *       callback(
		 *         JSON.parse( localStorage.getItem('dataTablesData') )
		 *       );
		 *     }
		 *   } );
		 */
		"ajax": null,
	
	
		/**
		 * This parameter allows you to readily specify the entries in the length drop
		 * down menu that DataTables shows when pagination is enabled. It can be
		 * either a 1D array of options which will be used for both the displayed
		 * option and the value, or a 2D array which will use the array in the first
		 * position as the value, and the array in the second position as the
		 * displayed options (useful for language strings such as 'All').
		 *
		 * Note that the `pageLength` property will be automatically set to the
		 * first value given in this array, unless `pageLength` is also provided.
		 *  @type array
		 *  @default [ 10, 25, 50, 100 ]
		 *
		 *  @dtopt Option
		 *  @name DataTable.defaults.lengthMenu
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "lengthMenu": [[10, 25, 50, -1], [10, 25, 50, "All"]]
		 *      } );
		 *    } );
		 */
		"aLengthMenu": [ 10, 25, 50, 100 ],
	
	
		/**
		 * The `columns` option in the initialisation parameter allows you to define
		 * details about the way individual columns behave. For a full list of
		 * column options that can be set, please see
		 * {@link DataTable.defaults.column}. Note that if you use `columns` to
		 * define your columns, you must have an entry in the array for every single
		 * column that you have in your table (these can be null if you don't which
		 * to specify any options).
		 *  @member
		 *
		 *  @name DataTable.defaults.column
		 */
		"aoColumns": null,
	
		/**
		 * Very similar to `columns`, `columnDefs` allows you to target a specific
		 * column, multiple columns, or all columns, using the `targets` property of
		 * each object in the array. This allows great flexibility when creating
		 * tables, as the `columnDefs` arrays can be of any length, targeting the
		 * columns you specifically want. `columnDefs` may use any of the column
		 * options available: {@link DataTable.defaults.column}, but it _must_
		 * have `targets` defined in each object in the array. Values in the `targets`
		 * array may be:
		 *   <ul>
		 *     <li>a string - class name will be matched on the TH for the column</li>
		 *     <li>0 or a positive integer - column index counting from the left</li>
		 *     <li>a negative integer - column index counting from the right</li>
		 *     <li>the string "_all" - all columns (i.e. assign a default)</li>
		 *   </ul>
		 *  @member
		 *
		 *  @name DataTable.defaults.columnDefs
		 */
		"aoColumnDefs": null,
	
	
		/**
		 * Basically the same as `search`, this parameter defines the individual column
		 * filtering state at initialisation time. The array must be of the same size
		 * as the number of columns, and each element be an object with the parameters
		 * `search` and `escapeRegex` (the latter is optional). 'null' is also
		 * accepted and the default will be used.
		 *  @type array
		 *  @default []
		 *
		 *  @dtopt Option
		 *  @name DataTable.defaults.searchCols
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "searchCols": [
		 *          null,
		 *          { "search": "My filter" },
		 *          null,
		 *          { "search": "^[0-9]", "escapeRegex": false }
		 *        ]
		 *      } );
		 *    } )
		 */
		"aoSearchCols": [],
	
	
		/**
		 * An array of CSS classes that should be applied to displayed rows. This
		 * array may be of any length, and DataTables will apply each class
		 * sequentially, looping when required.
		 *  @type array
		 *  @default null <i>Will take the values determined by the `oClasses.stripe*`
		 *    options</i>
		 *
		 *  @dtopt Option
		 *  @name DataTable.defaults.stripeClasses
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "stripeClasses": [ 'strip1', 'strip2', 'strip3' ]
		 *      } );
		 *    } )
		 */
		"asStripeClasses": null,
	
	
		/**
		 * Enable or disable automatic column width calculation. This can be disabled
		 * as an optimisation (it takes some time to calculate the widths) if the
		 * tables widths are passed in using `columns`.
		 *  @type boolean
		 *  @default true
		 *
		 *  @dtopt Features
		 *  @name DataTable.defaults.autoWidth
		 *
		 *  @example
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "autoWidth": false
		 *      } );
		 *    } );
		 */
		"bAutoWidth": true,
	
	
		/**
		 * Deferred rendering can provide DataTables with a huge speed boost when you
		 * are using an Ajax or JS data source for the table. This option, when set to
		 * true, will cause DataTables to defer the creation of the table elements for
		 * each row until they are needed for a draw - saving a significant amount of
		 * time.
		 *  @type boolean
		 *  @default false
		 *
		 *  @dtopt Features
		 *  @name DataTable.defaults.deferRender
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "ajax": "sources/arrays.txt",
		 *        "deferRender": true
		 *      } );
		 *    } );
		 */
		"bDeferRender": false,
	
	
		/**
		 * Replace a DataTable which matches the given selector and replace it with
		 * one which has the properties of the new initialisation object passed. If no
		 * table matches the selector, then the new DataTable will be constructed as
		 * per normal.
		 *  @type boolean
		 *  @default false
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.destroy
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "srollY": "200px",
		 *        "paginate": false
		 *      } );
		 *
		 *      // Some time later....
		 *      $('#example').dataTable( {
		 *        "filter": false,
		 *        "destroy": true
		 *      } );
		 *    } );
		 */
		"bDestroy": false,
	
	
		/**
		 * Enable or disable filtering of data. Filtering in DataTables is "smart" in
		 * that it allows the end user to input multiple words (space separated) and
		 * will match a row containing those words, even if not in the order that was
		 * specified (this allow matching across multiple columns). Note that if you
		 * wish to use filtering in DataTables this must remain 'true' - to remove the
		 * default filtering input box and retain filtering abilities, please use
		 * {@link DataTable.defaults.dom}.
		 *  @type boolean
		 *  @default true
		 *
		 *  @dtopt Features
		 *  @name DataTable.defaults.searching
		 *
		 *  @example
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "searching": false
		 *      } );
		 *    } );
		 */
		"bFilter": true,
	
	
		/**
		 * Enable or disable the table information display. This shows information
		 * about the data that is currently visible on the page, including information
		 * about filtered data if that action is being performed.
		 *  @type boolean
		 *  @default true
		 *
		 *  @dtopt Features
		 *  @name DataTable.defaults.info
		 *
		 *  @example
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "info": false
		 *      } );
		 *    } );
		 */
		"bInfo": true,
	
	
		/**
		 * Allows the end user to select the size of a formatted page from a select
		 * menu (sizes are 10, 25, 50 and 100). Requires pagination (`paginate`).
		 *  @type boolean
		 *  @default true
		 *
		 *  @dtopt Features
		 *  @name DataTable.defaults.lengthChange
		 *
		 *  @example
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "lengthChange": false
		 *      } );
		 *    } );
		 */
		"bLengthChange": true,
	
	
		/**
		 * Enable or disable pagination.
		 *  @type boolean
		 *  @default true
		 *
		 *  @dtopt Features
		 *  @name DataTable.defaults.paging
		 *
		 *  @example
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "paging": false
		 *      } );
		 *    } );
		 */
		"bPaginate": true,
	
	
		/**
		 * Enable or disable the display of a 'processing' indicator when the table is
		 * being processed (e.g. a sort). This is particularly useful for tables with
		 * large amounts of data where it can take a noticeable amount of time to sort
		 * the entries.
		 *  @type boolean
		 *  @default false
		 *
		 *  @dtopt Features
		 *  @name DataTable.defaults.processing
		 *
		 *  @example
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "processing": true
		 *      } );
		 *    } );
		 */
		"bProcessing": false,
	
	
		/**
		 * Retrieve the DataTables object for the given selector. Note that if the
		 * table has already been initialised, this parameter will cause DataTables
		 * to simply return the object that has already been set up - it will not take
		 * account of any changes you might have made to the initialisation object
		 * passed to DataTables (setting this parameter to true is an acknowledgement
		 * that you understand this). `destroy` can be used to reinitialise a table if
		 * you need.
		 *  @type boolean
		 *  @default false
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.retrieve
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      initTable();
		 *      tableActions();
		 *    } );
		 *
		 *    function initTable ()
		 *    {
		 *      return $('#example').dataTable( {
		 *        "scrollY": "200px",
		 *        "paginate": false,
		 *        "retrieve": true
		 *      } );
		 *    }
		 *
		 *    function tableActions ()
		 *    {
		 *      var table = initTable();
		 *      // perform API operations with oTable
		 *    }
		 */
		"bRetrieve": false,
	
	
		/**
		 * When vertical (y) scrolling is enabled, DataTables will force the height of
		 * the table's viewport to the given height at all times (useful for layout).
		 * However, this can look odd when filtering data down to a small data set,
		 * and the footer is left "floating" further down. This parameter (when
		 * enabled) will cause DataTables to collapse the table's viewport down when
		 * the result set will fit within the given Y height.
		 *  @type boolean
		 *  @default false
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.scrollCollapse
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "scrollY": "200",
		 *        "scrollCollapse": true
		 *      } );
		 *    } );
		 */
		"bScrollCollapse": false,
	
	
		/**
		 * Configure DataTables to use server-side processing. Note that the
		 * `ajax` parameter must also be given in order to give DataTables a
		 * source to obtain the required data for each draw.
		 *  @type boolean
		 *  @default false
		 *
		 *  @dtopt Features
		 *  @dtopt Server-side
		 *  @name DataTable.defaults.serverSide
		 *
		 *  @example
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "serverSide": true,
		 *        "ajax": "xhr.php"
		 *      } );
		 *    } );
		 */
		"bServerSide": false,
	
	
		/**
		 * Enable or disable sorting of columns. Sorting of individual columns can be
		 * disabled by the `sortable` option for each column.
		 *  @type boolean
		 *  @default true
		 *
		 *  @dtopt Features
		 *  @name DataTable.defaults.ordering
		 *
		 *  @example
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "ordering": false
		 *      } );
		 *    } );
		 */
		"bSort": true,
	
	
		/**
		 * Enable or display DataTables' ability to sort multiple columns at the
		 * same time (activated by shift-click by the user).
		 *  @type boolean
		 *  @default true
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.orderMulti
		 *
		 *  @example
		 *    // Disable multiple column sorting ability
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "orderMulti": false
		 *      } );
		 *    } );
		 */
		"bSortMulti": true,
	
	
		/**
		 * Allows control over whether DataTables should use the top (true) unique
		 * cell that is found for a single column, or the bottom (false - default).
		 * This is useful when using complex headers.
		 *  @type boolean
		 *  @default false
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.orderCellsTop
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "orderCellsTop": true
		 *      } );
		 *    } );
		 */
		"bSortCellsTop": false,
	
	
		/**
		 * Enable or disable the addition of the classes `sorting\_1`, `sorting\_2` and
		 * `sorting\_3` to the columns which are currently being sorted on. This is
		 * presented as a feature switch as it can increase processing time (while
		 * classes are removed and added) so for large data sets you might want to
		 * turn this off.
		 *  @type boolean
		 *  @default true
		 *
		 *  @dtopt Features
		 *  @name DataTable.defaults.orderClasses
		 *
		 *  @example
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "orderClasses": false
		 *      } );
		 *    } );
		 */
		"bSortClasses": true,
	
	
		/**
		 * Enable or disable state saving. When enabled HTML5 `localStorage` will be
		 * used to save table display information such as pagination information,
		 * display length, filtering and sorting. As such when the end user reloads
		 * the page the display display will match what thy had previously set up.
		 *
		 * Due to the use of `localStorage` the default state saving is not supported
		 * in IE6 or 7. If state saving is required in those browsers, use
		 * `stateSaveCallback` to provide a storage solution such as cookies.
		 *  @type boolean
		 *  @default false
		 *
		 *  @dtopt Features
		 *  @name DataTable.defaults.stateSave
		 *
		 *  @example
		 *    $(document).ready( function () {
		 *      $('#example').dataTable( {
		 *        "stateSave": true
		 *      } );
		 *    } );
		 */
		"bStateSave": false,
	
	
		/**
		 * This function is called when a TR element is created (and all TD child
		 * elements have been inserted), or registered if using a DOM source, allowing
		 * manipulation of the TR element (adding classes etc).
		 *  @type function
		 *  @param {node} row "TR" element for the current row
		 *  @param {array} data Raw data array for this row
		 *  @param {int} dataIndex The index of this row in the internal aoData array
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.createdRow
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "createdRow": function( row, data, dataIndex ) {
		 *          // Bold the grade for all 'A' grade browsers
		 *          if ( data[4] == "A" )
		 *          {
		 *            $('td:eq(4)', row).html( '<b>A</b>' );
		 *          }
		 *        }
		 *      } );
		 *    } );
		 */
		"fnCreatedRow": null,
	
	
		/**
		 * This function is called on every 'draw' event, and allows you to
		 * dynamically modify any aspect you want about the created DOM.
		 *  @type function
		 *  @param {object} settings DataTables settings object
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.drawCallback
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "drawCallback": function( settings ) {
		 *          alert( 'DataTables has redrawn the table' );
		 *        }
		 *      } );
		 *    } );
		 */
		"fnDrawCallback": null,
	
	
		/**
		 * Identical to fnHeaderCallback() but for the table footer this function
		 * allows you to modify the table footer on every 'draw' event.
		 *  @type function
		 *  @param {node} foot "TR" element for the footer
		 *  @param {array} data Full table data (as derived from the original HTML)
		 *  @param {int} start Index for the current display starting point in the
		 *    display array
		 *  @param {int} end Index for the current display ending point in the
		 *    display array
		 *  @param {array int} display Index array to translate the visual position
		 *    to the full data array
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.footerCallback
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "footerCallback": function( tfoot, data, start, end, display ) {
		 *          tfoot.getElementsByTagName('th')[0].innerHTML = "Starting index is "+start;
		 *        }
		 *      } );
		 *    } )
		 */
		"fnFooterCallback": null,
	
	
		/**
		 * When rendering large numbers in the information element for the table
		 * (i.e. "Showing 1 to 10 of 57 entries") DataTables will render large numbers
		 * to have a comma separator for the 'thousands' units (e.g. 1 million is
		 * rendered as "1,000,000") to help readability for the end user. This
		 * function will override the default method DataTables uses.
		 *  @type function
		 *  @member
		 *  @param {int} toFormat number to be formatted
		 *  @returns {string} formatted string for DataTables to show the number
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.formatNumber
		 *
		 *  @example
		 *    // Format a number using a single quote for the separator (note that
		 *    // this can also be done with the language.thousands option)
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "formatNumber": function ( toFormat ) {
		 *          return toFormat.toString().replace(
		 *            /\B(?=(\d{3})+(?!\d))/g, "'"
		 *          );
		 *        };
		 *      } );
		 *    } );
		 */
		"fnFormatNumber": function ( toFormat ) {
			return toFormat.toString().replace(
				/\B(?=(\d{3})+(?!\d))/g,
				this.oLanguage.sThousands
			);
		},
	
	
		/**
		 * This function is called on every 'draw' event, and allows you to
		 * dynamically modify the header row. This can be used to calculate and
		 * display useful information about the table.
		 *  @type function
		 *  @param {node} head "TR" element for the header
		 *  @param {array} data Full table data (as derived from the original HTML)
		 *  @param {int} start Index for the current display starting point in the
		 *    display array
		 *  @param {int} end Index for the current display ending point in the
		 *    display array
		 *  @param {array int} display Index array to translate the visual position
		 *    to the full data array
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.headerCallback
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "fheaderCallback": function( head, data, start, end, display ) {
		 *          head.getElementsByTagName('th')[0].innerHTML = "Displaying "+(end-start)+" records";
		 *        }
		 *      } );
		 *    } )
		 */
		"fnHeaderCallback": null,
	
	
		/**
		 * The information element can be used to convey information about the current
		 * state of the table. Although the internationalisation options presented by
		 * DataTables are quite capable of dealing with most customisations, there may
		 * be times where you wish to customise the string further. This callback
		 * allows you to do exactly that.
		 *  @type function
		 *  @param {object} oSettings DataTables settings object
		 *  @param {int} start Starting position in data for the draw
		 *  @param {int} end End position in data for the draw
		 *  @param {int} max Total number of rows in the table (regardless of
		 *    filtering)
		 *  @param {int} total Total number of rows in the data set, after filtering
		 *  @param {string} pre The string that DataTables has formatted using it's
		 *    own rules
		 *  @returns {string} The string to be displayed in the information element.
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.infoCallback
		 *
		 *  @example
		 *    $('#example').dataTable( {
		 *      "infoCallback": function( settings, start, end, max, total, pre ) {
		 *        return start +" to "+ end;
		 *      }
		 *    } );
		 */
		"fnInfoCallback": null,
	
	
		/**
		 * Called when the table has been initialised. Normally DataTables will
		 * initialise sequentially and there will be no need for this function,
		 * however, this does not hold true when using external language information
		 * since that is obtained using an async XHR call.
		 *  @type function
		 *  @param {object} settings DataTables settings object
		 *  @param {object} json The JSON object request from the server - only
		 *    present if client-side Ajax sourced data is used
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.initComplete
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "initComplete": function(settings, json) {
		 *          alert( 'DataTables has finished its initialisation.' );
		 *        }
		 *      } );
		 *    } )
		 */
		"fnInitComplete": null,
	
	
		/**
		 * Called at the very start of each table draw and can be used to cancel the
		 * draw by returning false, any other return (including undefined) results in
		 * the full draw occurring).
		 *  @type function
		 *  @param {object} settings DataTables settings object
		 *  @returns {boolean} False will cancel the draw, anything else (including no
		 *    return) will allow it to complete.
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.preDrawCallback
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "preDrawCallback": function( settings ) {
		 *          if ( $('#test').val() == 1 ) {
		 *            return false;
		 *          }
		 *        }
		 *      } );
		 *    } );
		 */
		"fnPreDrawCallback": null,
	
	
		/**
		 * This function allows you to 'post process' each row after it have been
		 * generated for each table draw, but before it is rendered on screen. This
		 * function might be used for setting the row class name etc.
		 *  @type function
		 *  @param {node} row "TR" element for the current row
		 *  @param {array} data Raw data array for this row
		 *  @param {int} displayIndex The display index for the current table draw
		 *  @param {int} displayIndexFull The index of the data in the full list of
		 *    rows (after filtering)
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.rowCallback
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "rowCallback": function( row, data, displayIndex, displayIndexFull ) {
		 *          // Bold the grade for all 'A' grade browsers
		 *          if ( data[4] == "A" ) {
		 *            $('td:eq(4)', row).html( '<b>A</b>' );
		 *          }
		 *        }
		 *      } );
		 *    } );
		 */
		"fnRowCallback": null,
	
	
		/**
		 * __Deprecated__ The functionality provided by this parameter has now been
		 * superseded by that provided through `ajax`, which should be used instead.
		 *
		 * This parameter allows you to override the default function which obtains
		 * the data from the server so something more suitable for your application.
		 * For example you could use POST data, or pull information from a Gears or
		 * AIR database.
		 *  @type function
		 *  @member
		 *  @param {string} source HTTP source to obtain the data from (`ajax`)
		 *  @param {array} data A key/value pair object containing the data to send
		 *    to the server
		 *  @param {function} callback to be called on completion of the data get
		 *    process that will draw the data on the page.
		 *  @param {object} settings DataTables settings object
		 *
		 *  @dtopt Callbacks
		 *  @dtopt Server-side
		 *  @name DataTable.defaults.serverData
		 *
		 *  @deprecated 1.10. Please use `ajax` for this functionality now.
		 */
		"fnServerData": null,
	
	
		/**
		 * __Deprecated__ The functionality provided by this parameter has now been
		 * superseded by that provided through `ajax`, which should be used instead.
		 *
		 *  It is often useful to send extra data to the server when making an Ajax
		 * request - for example custom filtering information, and this callback
		 * function makes it trivial to send extra information to the server. The
		 * passed in parameter is the data set that has been constructed by
		 * DataTables, and you can add to this or modify it as you require.
		 *  @type function
		 *  @param {array} data Data array (array of objects which are name/value
		 *    pairs) that has been constructed by DataTables and will be sent to the
		 *    server. In the case of Ajax sourced data with server-side processing
		 *    this will be an empty array, for server-side processing there will be a
		 *    significant number of parameters!
		 *  @returns {undefined} Ensure that you modify the data array passed in,
		 *    as this is passed by reference.
		 *
		 *  @dtopt Callbacks
		 *  @dtopt Server-side
		 *  @name DataTable.defaults.serverParams
		 *
		 *  @deprecated 1.10. Please use `ajax` for this functionality now.
		 */
		"fnServerParams": null,
	
	
		/**
		 * Load the table state. With this function you can define from where, and how, the
		 * state of a table is loaded. By default DataTables will load from `localStorage`
		 * but you might wish to use a server-side database or cookies.
		 *  @type function
		 *  @member
		 *  @param {object} settings DataTables settings object
		 *  @param {object} callback Callback that can be executed when done. It
		 *    should be passed the loaded state object.
		 *  @return {object} The DataTables state object to be loaded
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.stateLoadCallback
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "stateSave": true,
		 *        "stateLoadCallback": function (settings, callback) {
		 *          $.ajax( {
		 *            "url": "/state_load",
		 *            "dataType": "json",
		 *            "success": function (json) {
		 *              callback( json );
		 *            }
		 *          } );
		 *        }
		 *      } );
		 *    } );
		 */
		"fnStateLoadCallback": function ( settings ) {
			try {
				return JSON.parse(
					(settings.iStateDuration === -1 ? sessionStorage : localStorage).getItem(
						'DataTables_'+settings.sInstance+'_'+location.pathname
					)
				);
			} catch (e) {}
		},
	
	
		/**
		 * Callback which allows modification of the saved state prior to loading that state.
		 * This callback is called when the table is loading state from the stored data, but
		 * prior to the settings object being modified by the saved state. Note that for
		 * plug-in authors, you should use the `stateLoadParams` event to load parameters for
		 * a plug-in.
		 *  @type function
		 *  @param {object} settings DataTables settings object
		 *  @param {object} data The state object that is to be loaded
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.stateLoadParams
		 *
		 *  @example
		 *    // Remove a saved filter, so filtering is never loaded
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "stateSave": true,
		 *        "stateLoadParams": function (settings, data) {
		 *          data.oSearch.sSearch = "";
		 *        }
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Disallow state loading by returning false
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "stateSave": true,
		 *        "stateLoadParams": function (settings, data) {
		 *          return false;
		 *        }
		 *      } );
		 *    } );
		 */
		"fnStateLoadParams": null,
	
	
		/**
		 * Callback that is called when the state has been loaded from the state saving method
		 * and the DataTables settings object has been modified as a result of the loaded state.
		 *  @type function
		 *  @param {object} settings DataTables settings object
		 *  @param {object} data The state object that was loaded
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.stateLoaded
		 *
		 *  @example
		 *    // Show an alert with the filtering value that was saved
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "stateSave": true,
		 *        "stateLoaded": function (settings, data) {
		 *          alert( 'Saved filter was: '+data.oSearch.sSearch );
		 *        }
		 *      } );
		 *    } );
		 */
		"fnStateLoaded": null,
	
	
		/**
		 * Save the table state. This function allows you to define where and how the state
		 * information for the table is stored By default DataTables will use `localStorage`
		 * but you might wish to use a server-side database or cookies.
		 *  @type function
		 *  @member
		 *  @param {object} settings DataTables settings object
		 *  @param {object} data The state object to be saved
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.stateSaveCallback
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "stateSave": true,
		 *        "stateSaveCallback": function (settings, data) {
		 *          // Send an Ajax request to the server with the state object
		 *          $.ajax( {
		 *            "url": "/state_save",
		 *            "data": data,
		 *            "dataType": "json",
		 *            "method": "POST"
		 *            "success": function () {}
		 *          } );
		 *        }
		 *      } );
		 *    } );
		 */
		"fnStateSaveCallback": function ( settings, data ) {
			try {
				(settings.iStateDuration === -1 ? sessionStorage : localStorage).setItem(
					'DataTables_'+settings.sInstance+'_'+location.pathname,
					JSON.stringify( data )
				);
			} catch (e) {}
		},
	
	
		/**
		 * Callback which allows modification of the state to be saved. Called when the table
		 * has changed state a new state save is required. This method allows modification of
		 * the state saving object prior to actually doing the save, including addition or
		 * other state properties or modification. Note that for plug-in authors, you should
		 * use the `stateSaveParams` event to save parameters for a plug-in.
		 *  @type function
		 *  @param {object} settings DataTables settings object
		 *  @param {object} data The state object to be saved
		 *
		 *  @dtopt Callbacks
		 *  @name DataTable.defaults.stateSaveParams
		 *
		 *  @example
		 *    // Remove a saved filter, so filtering is never saved
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "stateSave": true,
		 *        "stateSaveParams": function (settings, data) {
		 *          data.oSearch.sSearch = "";
		 *        }
		 *      } );
		 *    } );
		 */
		"fnStateSaveParams": null,
	
	
		/**
		 * Duration for which the saved state information is considered valid. After this period
		 * has elapsed the state will be returned to the default.
		 * Value is given in seconds.
		 *  @type int
		 *  @default 7200 <i>(2 hours)</i>
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.stateDuration
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "stateDuration": 60*60*24; // 1 day
		 *      } );
		 *    } )
		 */
		"iStateDuration": 7200,
	
	
		/**
		 * When enabled DataTables will not make a request to the server for the first
		 * page draw - rather it will use the data already on the page (no sorting etc
		 * will be applied to it), thus saving on an XHR at load time. `deferLoading`
		 * is used to indicate that deferred loading is required, but it is also used
		 * to tell DataTables how many records there are in the full table (allowing
		 * the information element and pagination to be displayed correctly). In the case
		 * where a filtering is applied to the table on initial load, this can be
		 * indicated by giving the parameter as an array, where the first element is
		 * the number of records available after filtering and the second element is the
		 * number of records without filtering (allowing the table information element
		 * to be shown correctly).
		 *  @type int | array
		 *  @default null
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.deferLoading
		 *
		 *  @example
		 *    // 57 records available in the table, no filtering applied
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "serverSide": true,
		 *        "ajax": "scripts/server_processing.php",
		 *        "deferLoading": 57
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // 57 records after filtering, 100 without filtering (an initial filter applied)
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "serverSide": true,
		 *        "ajax": "scripts/server_processing.php",
		 *        "deferLoading": [ 57, 100 ],
		 *        "search": {
		 *          "search": "my_filter"
		 *        }
		 *      } );
		 *    } );
		 */
		"iDeferLoading": null,
	
	
		/**
		 * Number of rows to display on a single page when using pagination. If
		 * feature enabled (`lengthChange`) then the end user will be able to override
		 * this to a custom setting using a pop-up menu.
		 *  @type int
		 *  @default 10
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.pageLength
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "pageLength": 50
		 *      } );
		 *    } )
		 */
		"iDisplayLength": 10,
	
	
		/**
		 * Define the starting point for data display when using DataTables with
		 * pagination. Note that this parameter is the number of records, rather than
		 * the page number, so if you have 10 records per page and want to start on
		 * the third page, it should be "20".
		 *  @type int
		 *  @default 0
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.displayStart
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "displayStart": 20
		 *      } );
		 *    } )
		 */
		"iDisplayStart": 0,
	
	
		/**
		 * By default DataTables allows keyboard navigation of the table (sorting, paging,
		 * and filtering) by adding a `tabindex` attribute to the required elements. This
		 * allows you to tab through the controls and press the enter key to activate them.
		 * The tabindex is default 0, meaning that the tab follows the flow of the document.
		 * You can overrule this using this parameter if you wish. Use a value of -1 to
		 * disable built-in keyboard navigation.
		 *  @type int
		 *  @default 0
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.tabIndex
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "tabIndex": 1
		 *      } );
		 *    } );
		 */
		"iTabIndex": 0,
	
	
		/**
		 * Classes that DataTables assigns to the various components and features
		 * that it adds to the HTML table. This allows classes to be configured
		 * during initialisation in addition to through the static
		 * {@link DataTable.ext.oStdClasses} object).
		 *  @namespace
		 *  @name DataTable.defaults.classes
		 */
		"oClasses": {},
	
	
		/**
		 * All strings that DataTables uses in the user interface that it creates
		 * are defined in this object, allowing you to modified them individually or
		 * completely replace them all as required.
		 *  @namespace
		 *  @name DataTable.defaults.language
		 */
		"oLanguage": {
			/**
			 * Strings that are used for WAI-ARIA labels and controls only (these are not
			 * actually visible on the page, but will be read by screenreaders, and thus
			 * must be internationalised as well).
			 *  @namespace
			 *  @name DataTable.defaults.language.aria
			 */
			"oAria": {
				/**
				 * ARIA label that is added to the table headers when the column may be
				 * sorted ascending by activing the column (click or return when focused).
				 * Note that the column header is prefixed to this string.
				 *  @type string
				 *  @default : activate to sort column ascending
				 *
				 *  @dtopt Language
				 *  @name DataTable.defaults.language.aria.sortAscending
				 *
				 *  @example
				 *    $(document).ready( function() {
				 *      $('#example').dataTable( {
				 *        "language": {
				 *          "aria": {
				 *            "sortAscending": " - click/return to sort ascending"
				 *          }
				 *        }
				 *      } );
				 *    } );
				 */
				"sSortAscending": ": activate to sort column ascending",
	
				/**
				 * ARIA label that is added to the table headers when the column may be
				 * sorted descending by activing the column (click or return when focused).
				 * Note that the column header is prefixed to this string.
				 *  @type string
				 *  @default : activate to sort column ascending
				 *
				 *  @dtopt Language
				 *  @name DataTable.defaults.language.aria.sortDescending
				 *
				 *  @example
				 *    $(document).ready( function() {
				 *      $('#example').dataTable( {
				 *        "language": {
				 *          "aria": {
				 *            "sortDescending": " - click/return to sort descending"
				 *          }
				 *        }
				 *      } );
				 *    } );
				 */
				"sSortDescending": ": activate to sort column descending"
			},
	
			/**
			 * Pagination string used by DataTables for the built-in pagination
			 * control types.
			 *  @namespace
			 *  @name DataTable.defaults.language.paginate
			 */
			"oPaginate": {
				/**
				 * Text to use when using the 'full_numbers' type of pagination for the
				 * button to take the user to the first page.
				 *  @type string
				 *  @default First
				 *
				 *  @dtopt Language
				 *  @name DataTable.defaults.language.paginate.first
				 *
				 *  @example
				 *    $(document).ready( function() {
				 *      $('#example').dataTable( {
				 *        "language": {
				 *          "paginate": {
				 *            "first": "First page"
				 *          }
				 *        }
				 *      } );
				 *    } );
				 */
				"sFirst": "First",
	
	
				/**
				 * Text to use when using the 'full_numbers' type of pagination for the
				 * button to take the user to the last page.
				 *  @type string
				 *  @default Last
				 *
				 *  @dtopt Language
				 *  @name DataTable.defaults.language.paginate.last
				 *
				 *  @example
				 *    $(document).ready( function() {
				 *      $('#example').dataTable( {
				 *        "language": {
				 *          "paginate": {
				 *            "last": "Last page"
				 *          }
				 *        }
				 *      } );
				 *    } );
				 */
				"sLast": "Last",
	
	
				/**
				 * Text to use for the 'next' pagination button (to take the user to the
				 * next page).
				 *  @type string
				 *  @default Next
				 *
				 *  @dtopt Language
				 *  @name DataTable.defaults.language.paginate.next
				 *
				 *  @example
				 *    $(document).ready( function() {
				 *      $('#example').dataTable( {
				 *        "language": {
				 *          "paginate": {
				 *            "next": "Next page"
				 *          }
				 *        }
				 *      } );
				 *    } );
				 */
				"sNext": "Next",
	
	
				/**
				 * Text to use for the 'previous' pagination button (to take the user to
				 * the previous page).
				 *  @type string
				 *  @default Previous
				 *
				 *  @dtopt Language
				 *  @name DataTable.defaults.language.paginate.previous
				 *
				 *  @example
				 *    $(document).ready( function() {
				 *      $('#example').dataTable( {
				 *        "language": {
				 *          "paginate": {
				 *            "previous": "Previous page"
				 *          }
				 *        }
				 *      } );
				 *    } );
				 */
				"sPrevious": "Previous"
			},
	
			/**
			 * This string is shown in preference to `zeroRecords` when the table is
			 * empty of data (regardless of filtering). Note that this is an optional
			 * parameter - if it is not given, the value of `zeroRecords` will be used
			 * instead (either the default or given value).
			 *  @type string
			 *  @default No data available in table
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.emptyTable
			 *
			 *  @example
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "emptyTable": "No data available in table"
			 *        }
			 *      } );
			 *    } );
			 */
			"sEmptyTable": "No data available in table",
	
	
			/**
			 * This string gives information to the end user about the information
			 * that is current on display on the page. The following tokens can be
			 * used in the string and will be dynamically replaced as the table
			 * display updates. This tokens can be placed anywhere in the string, or
			 * removed as needed by the language requires:
			 *
			 * * `\_START\_` - Display index of the first record on the current page
			 * * `\_END\_` - Display index of the last record on the current page
			 * * `\_TOTAL\_` - Number of records in the table after filtering
			 * * `\_MAX\_` - Number of records in the table without filtering
			 * * `\_PAGE\_` - Current page number
			 * * `\_PAGES\_` - Total number of pages of data in the table
			 *
			 *  @type string
			 *  @default Showing _START_ to _END_ of _TOTAL_ entries
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.info
			 *
			 *  @example
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "info": "Showing page _PAGE_ of _PAGES_"
			 *        }
			 *      } );
			 *    } );
			 */
			"sInfo": "Showing _START_ to _END_ of _TOTAL_ entries",
	
	
			/**
			 * Display information string for when the table is empty. Typically the
			 * format of this string should match `info`.
			 *  @type string
			 *  @default Showing 0 to 0 of 0 entries
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.infoEmpty
			 *
			 *  @example
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "infoEmpty": "No entries to show"
			 *        }
			 *      } );
			 *    } );
			 */
			"sInfoEmpty": "Showing 0 to 0 of 0 entries",
	
	
			/**
			 * When a user filters the information in a table, this string is appended
			 * to the information (`info`) to give an idea of how strong the filtering
			 * is. The variable _MAX_ is dynamically updated.
			 *  @type string
			 *  @default (filtered from _MAX_ total entries)
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.infoFiltered
			 *
			 *  @example
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "infoFiltered": " - filtering from _MAX_ records"
			 *        }
			 *      } );
			 *    } );
			 */
			"sInfoFiltered": "(filtered from _MAX_ total entries)",
	
	
			/**
			 * If can be useful to append extra information to the info string at times,
			 * and this variable does exactly that. This information will be appended to
			 * the `info` (`infoEmpty` and `infoFiltered` in whatever combination they are
			 * being used) at all times.
			 *  @type string
			 *  @default <i>Empty string</i>
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.infoPostFix
			 *
			 *  @example
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "infoPostFix": "All records shown are derived from real information."
			 *        }
			 *      } );
			 *    } );
			 */
			"sInfoPostFix": "",
	
	
			/**
			 * This decimal place operator is a little different from the other
			 * language options since DataTables doesn't output floating point
			 * numbers, so it won't ever use this for display of a number. Rather,
			 * what this parameter does is modify the sort methods of the table so
			 * that numbers which are in a format which has a character other than
			 * a period (`.`) as a decimal place will be sorted numerically.
			 *
			 * Note that numbers with different decimal places cannot be shown in
			 * the same table and still be sortable, the table must be consistent.
			 * However, multiple different tables on the page can use different
			 * decimal place characters.
			 *  @type string
			 *  @default 
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.decimal
			 *
			 *  @example
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "decimal": ","
			 *          "thousands": "."
			 *        }
			 *      } );
			 *    } );
			 */
			"sDecimal": "",
	
	
			/**
			 * DataTables has a build in number formatter (`formatNumber`) which is
			 * used to format large numbers that are used in the table information.
			 * By default a comma is used, but this can be trivially changed to any
			 * character you wish with this parameter.
			 *  @type string
			 *  @default ,
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.thousands
			 *
			 *  @example
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "thousands": "'"
			 *        }
			 *      } );
			 *    } );
			 */
			"sThousands": ",",
	
	
			/**
			 * Detail the action that will be taken when the drop down menu for the
			 * pagination length option is changed. The '_MENU_' variable is replaced
			 * with a default select list of 10, 25, 50 and 100, and can be replaced
			 * with a custom select box if required.
			 *  @type string
			 *  @default Show _MENU_ entries
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.lengthMenu
			 *
			 *  @example
			 *    // Language change only
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "lengthMenu": "Display _MENU_ records"
			 *        }
			 *      } );
			 *    } );
			 *
			 *  @example
			 *    // Language and options change
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "lengthMenu": 'Display <select>'+
			 *            '<option value="10">10</option>'+
			 *            '<option value="20">20</option>'+
			 *            '<option value="30">30</option>'+
			 *            '<option value="40">40</option>'+
			 *            '<option value="50">50</option>'+
			 *            '<option value="-1">All</option>'+
			 *            '</select> records'
			 *        }
			 *      } );
			 *    } );
			 */
			"sLengthMenu": "Show _MENU_ entries",
	
	
			/**
			 * When using Ajax sourced data and during the first draw when DataTables is
			 * gathering the data, this message is shown in an empty row in the table to
			 * indicate to the end user the the data is being loaded. Note that this
			 * parameter is not used when loading data by server-side processing, just
			 * Ajax sourced data with client-side processing.
			 *  @type string
			 *  @default Loading...
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.loadingRecords
			 *
			 *  @example
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "loadingRecords": "Please wait - loading..."
			 *        }
			 *      } );
			 *    } );
			 */
			"sLoadingRecords": "Loading...",
	
	
			/**
			 * Text which is displayed when the table is processing a user action
			 * (usually a sort command or similar).
			 *  @type string
			 *  @default Processing...
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.processing
			 *
			 *  @example
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "processing": "DataTables is currently busy"
			 *        }
			 *      } );
			 *    } );
			 */
			"sProcessing": "Processing...",
	
	
			/**
			 * Details the actions that will be taken when the user types into the
			 * filtering input text box. The variable "_INPUT_", if used in the string,
			 * is replaced with the HTML text box for the filtering input allowing
			 * control over where it appears in the string. If "_INPUT_" is not given
			 * then the input box is appended to the string automatically.
			 *  @type string
			 *  @default Search:
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.search
			 *
			 *  @example
			 *    // Input text box will be appended at the end automatically
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "search": "Filter records:"
			 *        }
			 *      } );
			 *    } );
			 *
			 *  @example
			 *    // Specify where the filter should appear
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "search": "Apply filter _INPUT_ to table"
			 *        }
			 *      } );
			 *    } );
			 */
			"sSearch": "Search:",
	
	
			/**
			 * Assign a `placeholder` attribute to the search `input` element
			 *  @type string
			 *  @default 
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.searchPlaceholder
			 */
			"sSearchPlaceholder": "",
	
	
			/**
			 * All of the language information can be stored in a file on the
			 * server-side, which DataTables will look up if this parameter is passed.
			 * It must store the URL of the language file, which is in a JSON format,
			 * and the object has the same properties as the oLanguage object in the
			 * initialiser object (i.e. the above parameters). Please refer to one of
			 * the example language files to see how this works in action.
			 *  @type string
			 *  @default <i>Empty string - i.e. disabled</i>
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.url
			 *
			 *  @example
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "url": "http://www.sprymedia.co.uk/dataTables/lang.txt"
			 *        }
			 *      } );
			 *    } );
			 */
			"sUrl": "",
	
	
			/**
			 * Text shown inside the table records when the is no information to be
			 * displayed after filtering. `emptyTable` is shown when there is simply no
			 * information in the table at all (regardless of filtering).
			 *  @type string
			 *  @default No matching records found
			 *
			 *  @dtopt Language
			 *  @name DataTable.defaults.language.zeroRecords
			 *
			 *  @example
			 *    $(document).ready( function() {
			 *      $('#example').dataTable( {
			 *        "language": {
			 *          "zeroRecords": "No records to display"
			 *        }
			 *      } );
			 *    } );
			 */
			"sZeroRecords": "No matching records found"
		},
	
	
		/**
		 * This parameter allows you to have define the global filtering state at
		 * initialisation time. As an object the `search` parameter must be
		 * defined, but all other parameters are optional. When `regex` is true,
		 * the search string will be treated as a regular expression, when false
		 * (default) it will be treated as a straight string. When `smart`
		 * DataTables will use it's smart filtering methods (to word match at
		 * any point in the data), when false this will not be done.
		 *  @namespace
		 *  @extends DataTable.models.oSearch
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.search
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "search": {"search": "Initial search"}
		 *      } );
		 *    } )
		 */
		"oSearch": $.extend( {}, DataTable.models.oSearch ),
	
	
		/**
		 * __Deprecated__ The functionality provided by this parameter has now been
		 * superseded by that provided through `ajax`, which should be used instead.
		 *
		 * By default DataTables will look for the property `data` (or `aaData` for
		 * compatibility with DataTables 1.9-) when obtaining data from an Ajax
		 * source or for server-side processing - this parameter allows that
		 * property to be changed. You can use Javascript dotted object notation to
		 * get a data source for multiple levels of nesting.
		 *  @type string
		 *  @default data
		 *
		 *  @dtopt Options
		 *  @dtopt Server-side
		 *  @name DataTable.defaults.ajaxDataProp
		 *
		 *  @deprecated 1.10. Please use `ajax` for this functionality now.
		 */
		"sAjaxDataProp": "data",
	
	
		/**
		 * __Deprecated__ The functionality provided by this parameter has now been
		 * superseded by that provided through `ajax`, which should be used instead.
		 *
		 * You can instruct DataTables to load data from an external
		 * source using this parameter (use aData if you want to pass data in you
		 * already have). Simply provide a url a JSON object can be obtained from.
		 *  @type string
		 *  @default null
		 *
		 *  @dtopt Options
		 *  @dtopt Server-side
		 *  @name DataTable.defaults.ajaxSource
		 *
		 *  @deprecated 1.10. Please use `ajax` for this functionality now.
		 */
		"sAjaxSource": null,
	
	
		/**
		 * This initialisation variable allows you to specify exactly where in the
		 * DOM you want DataTables to inject the various controls it adds to the page
		 * (for example you might want the pagination controls at the top of the
		 * table). DIV elements (with or without a custom class) can also be added to
		 * aid styling. The follow syntax is used:
		 *   <ul>
		 *     <li>The following options are allowed:
		 *       <ul>
		 *         <li>'l' - Length changing</li>
		 *         <li>'f' - Filtering input</li>
		 *         <li>'t' - The table!</li>
		 *         <li>'i' - Information</li>
		 *         <li>'p' - Pagination</li>
		 *         <li>'r' - pRocessing</li>
		 *       </ul>
		 *     </li>
		 *     <li>The following constants are allowed:
		 *       <ul>
		 *         <li>'H' - jQueryUI theme "header" classes ('fg-toolbar ui-widget-header ui-corner-tl ui-corner-tr ui-helper-clearfix')</li>
		 *         <li>'F' - jQueryUI theme "footer" classes ('fg-toolbar ui-widget-header ui-corner-bl ui-corner-br ui-helper-clearfix')</li>
		 *       </ul>
		 *     </li>
		 *     <li>The following syntax is expected:
		 *       <ul>
		 *         <li>'&lt;' and '&gt;' - div elements</li>
		 *         <li>'&lt;"class" and '&gt;' - div with a class</li>
		 *         <li>'&lt;"#id" and '&gt;' - div with an ID</li>
		 *       </ul>
		 *     </li>
		 *     <li>Examples:
		 *       <ul>
		 *         <li>'&lt;"wrapper"flipt&gt;'</li>
		 *         <li>'&lt;lf&lt;t&gt;ip&gt;'</li>
		 *       </ul>
		 *     </li>
		 *   </ul>
		 *  @type string
		 *  @default lfrtip <i>(when `jQueryUI` is false)</i> <b>or</b>
		 *    <"H"lfr>t<"F"ip> <i>(when `jQueryUI` is true)</i>
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.dom
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "dom": '&lt;"top"i&gt;rt&lt;"bottom"flp&gt;&lt;"clear"&gt;'
		 *      } );
		 *    } );
		 */
		"sDom": "lfrtip",
	
	
		/**
		 * Search delay option. This will throttle full table searches that use the
		 * DataTables provided search input element (it does not effect calls to
		 * `dt-api search()`, providing a delay before the search is made.
		 *  @type integer
		 *  @default 0
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.searchDelay
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "searchDelay": 200
		 *      } );
		 *    } )
		 */
		"searchDelay": null,
	
	
		/**
		 * DataTables features six different built-in options for the buttons to
		 * display for pagination control:
		 *
		 * * `numbers` - Page number buttons only
		 * * `simple` - 'Previous' and 'Next' buttons only
		 * * 'simple_numbers` - 'Previous' and 'Next' buttons, plus page numbers
		 * * `full` - 'First', 'Previous', 'Next' and 'Last' buttons
		 * * `full_numbers` - 'First', 'Previous', 'Next' and 'Last' buttons, plus page numbers
		 * * `first_last_numbers` - 'First' and 'Last' buttons, plus page numbers
		 *  
		 * Further methods can be added using {@link DataTable.ext.oPagination}.
		 *  @type string
		 *  @default simple_numbers
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.pagingType
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "pagingType": "full_numbers"
		 *      } );
		 *    } )
		 */
		"sPaginationType": "simple_numbers",
	
	
		/**
		 * Enable horizontal scrolling. When a table is too wide to fit into a
		 * certain layout, or you have a large number of columns in the table, you
		 * can enable x-scrolling to show the table in a viewport, which can be
		 * scrolled. This property can be `true` which will allow the table to
		 * scroll horizontally when needed, or any CSS unit, or a number (in which
		 * case it will be treated as a pixel measurement). Setting as simply `true`
		 * is recommended.
		 *  @type boolean|string
		 *  @default <i>blank string - i.e. disabled</i>
		 *
		 *  @dtopt Features
		 *  @name DataTable.defaults.scrollX
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "scrollX": true,
		 *        "scrollCollapse": true
		 *      } );
		 *    } );
		 */
		"sScrollX": "",
	
	
		/**
		 * This property can be used to force a DataTable to use more width than it
		 * might otherwise do when x-scrolling is enabled. For example if you have a
		 * table which requires to be well spaced, this parameter is useful for
		 * "over-sizing" the table, and thus forcing scrolling. This property can by
		 * any CSS unit, or a number (in which case it will be treated as a pixel
		 * measurement).
		 *  @type string
		 *  @default <i>blank string - i.e. disabled</i>
		 *
		 *  @dtopt Options
		 *  @name DataTable.defaults.scrollXInner
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "scrollX": "100%",
		 *        "scrollXInner": "110%"
		 *      } );
		 *    } );
		 */
		"sScrollXInner": "",
	
	
		/**
		 * Enable vertical scrolling. Vertical scrolling will constrain the DataTable
		 * to the given height, and enable scrolling for any data which overflows the
		 * current viewport. This can be used as an alternative to paging to display
		 * a lot of data in a small area (although paging and scrolling can both be
		 * enabled at the same time). This property can be any CSS unit, or a number
		 * (in which case it will be treated as a pixel measurement).
		 *  @type string
		 *  @default <i>blank string - i.e. disabled</i>
		 *
		 *  @dtopt Features
		 *  @name DataTable.defaults.scrollY
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "scrollY": "200px",
		 *        "paginate": false
		 *      } );
		 *    } );
		 */
		"sScrollY": "",
	
	
		/**
		 * __Deprecated__ The functionality provided by this parameter has now been
		 * superseded by that provided through `ajax`, which should be used instead.
		 *
		 * Set the HTTP method that is used to make the Ajax call for server-side
		 * processing or Ajax sourced data.
		 *  @type string
		 *  @default GET
		 *
		 *  @dtopt Options
		 *  @dtopt Server-side
		 *  @name DataTable.defaults.serverMethod
		 *
		 *  @deprecated 1.10. Please use `ajax` for this functionality now.
		 */
		"sServerMethod": "GET",
	
	
		/**
		 * DataTables makes use of renderers when displaying HTML elements for
		 * a table. These renderers can be added or modified by plug-ins to
		 * generate suitable mark-up for a site. For example the Bootstrap
		 * integration plug-in for DataTables uses a paging button renderer to
		 * display pagination buttons in the mark-up required by Bootstrap.
		 *
		 * For further information about the renderers available see
		 * DataTable.ext.renderer
		 *  @type string|object
		 *  @default null
		 *
		 *  @name DataTable.defaults.renderer
		 *
		 */
		"renderer": null,
	
	
		/**
		 * Set the data property name that DataTables should use to get a row's id
		 * to set as the `id` property in the node.
		 *  @type string
		 *  @default DT_RowId
		 *
		 *  @name DataTable.defaults.rowId
		 */
		"rowId": "DT_RowId"
	};
	
	_fnHungarianMap( DataTable.defaults );
	
	
	
	/*
	 * Developer note - See note in model.defaults.js about the use of Hungarian
	 * notation and camel case.
	 */
	
	/**
	 * Column options that can be given to DataTables at initialisation time.
	 *  @namespace
	 */
	DataTable.defaults.column = {
		/**
		 * Define which column(s) an order will occur on for this column. This
		 * allows a column's ordering to take multiple columns into account when
		 * doing a sort or use the data from a different column. For example first
		 * name / last name columns make sense to do a multi-column sort over the
		 * two columns.
		 *  @type array|int
		 *  @default null <i>Takes the value of the column index automatically</i>
		 *
		 *  @name DataTable.defaults.column.orderData
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columnDefs`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [
		 *          { "orderData": [ 0, 1 ], "targets": [ 0 ] },
		 *          { "orderData": [ 1, 0 ], "targets": [ 1 ] },
		 *          { "orderData": 2, "targets": [ 2 ] }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          { "orderData": [ 0, 1 ] },
		 *          { "orderData": [ 1, 0 ] },
		 *          { "orderData": 2 },
		 *          null,
		 *          null
		 *        ]
		 *      } );
		 *    } );
		 */
		"aDataSort": null,
		"iDataSort": -1,
	
	
		/**
		 * You can control the default ordering direction, and even alter the
		 * behaviour of the sort handler (i.e. only allow ascending ordering etc)
		 * using this parameter.
		 *  @type array
		 *  @default [ 'asc', 'desc' ]
		 *
		 *  @name DataTable.defaults.column.orderSequence
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columnDefs`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [
		 *          { "orderSequence": [ "asc" ], "targets": [ 1 ] },
		 *          { "orderSequence": [ "desc", "asc", "asc" ], "targets": [ 2 ] },
		 *          { "orderSequence": [ "desc" ], "targets": [ 3 ] }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          null,
		 *          { "orderSequence": [ "asc" ] },
		 *          { "orderSequence": [ "desc", "asc", "asc" ] },
		 *          { "orderSequence": [ "desc" ] },
		 *          null
		 *        ]
		 *      } );
		 *    } );
		 */
		"asSorting": [ 'asc', 'desc' ],
	
	
		/**
		 * Enable or disable filtering on the data in this column.
		 *  @type boolean
		 *  @default true
		 *
		 *  @name DataTable.defaults.column.searchable
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columnDefs`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [
		 *          { "searchable": false, "targets": [ 0 ] }
		 *        ] } );
		 *    } );
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          { "searchable": false },
		 *          null,
		 *          null,
		 *          null,
		 *          null
		 *        ] } );
		 *    } );
		 */
		"bSearchable": true,
	
	
		/**
		 * Enable or disable ordering on this column.
		 *  @type boolean
		 *  @default true
		 *
		 *  @name DataTable.defaults.column.orderable
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columnDefs`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [
		 *          { "orderable": false, "targets": [ 0 ] }
		 *        ] } );
		 *    } );
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          { "orderable": false },
		 *          null,
		 *          null,
		 *          null,
		 *          null
		 *        ] } );
		 *    } );
		 */
		"bSortable": true,
	
	
		/**
		 * Enable or disable the display of this column.
		 *  @type boolean
		 *  @default true
		 *
		 *  @name DataTable.defaults.column.visible
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columnDefs`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [
		 *          { "visible": false, "targets": [ 0 ] }
		 *        ] } );
		 *    } );
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          { "visible": false },
		 *          null,
		 *          null,
		 *          null,
		 *          null
		 *        ] } );
		 *    } );
		 */
		"bVisible": true,
	
	
		/**
		 * Developer definable function that is called whenever a cell is created (Ajax source,
		 * etc) or processed for input (DOM source). This can be used as a compliment to mRender
		 * allowing you to modify the DOM element (add background colour for example) when the
		 * element is available.
		 *  @type function
		 *  @param {element} td The TD node that has been created
		 *  @param {*} cellData The Data for the cell
		 *  @param {array|object} rowData The data for the whole row
		 *  @param {int} row The row index for the aoData data store
		 *  @param {int} col The column index for aoColumns
		 *
		 *  @name DataTable.defaults.column.createdCell
		 *  @dtopt Columns
		 *
		 *  @example
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [ {
		 *          "targets": [3],
		 *          "createdCell": function (td, cellData, rowData, row, col) {
		 *            if ( cellData == "1.7" ) {
		 *              $(td).css('color', 'blue')
		 *            }
		 *          }
		 *        } ]
		 *      });
		 *    } );
		 */
		"fnCreatedCell": null,
	
	
		/**
		 * This parameter has been replaced by `data` in DataTables to ensure naming
		 * consistency. `dataProp` can still be used, as there is backwards
		 * compatibility in DataTables for this option, but it is strongly
		 * recommended that you use `data` in preference to `dataProp`.
		 *  @name DataTable.defaults.column.dataProp
		 */
	
	
		/**
		 * This property can be used to read data from any data source property,
		 * including deeply nested objects / properties. `data` can be given in a
		 * number of different ways which effect its behaviour:
		 *
		 * * `integer` - treated as an array index for the data source. This is the
		 *   default that DataTables uses (incrementally increased for each column).
		 * * `string` - read an object property from the data source. There are
		 *   three 'special' options that can be used in the string to alter how
		 *   DataTables reads the data from the source object:
		 *    * `.` - Dotted Javascript notation. Just as you use a `.` in
		 *      Javascript to read from nested objects, so to can the options
		 *      specified in `data`. For example: `browser.version` or
		 *      `browser.name`. If your object parameter name contains a period, use
		 *      `\\` to escape it - i.e. `first\\.name`.
		 *    * `[]` - Array notation. DataTables can automatically combine data
		 *      from and array source, joining the data with the characters provided
		 *      between the two brackets. For example: `name[, ]` would provide a
		 *      comma-space separated list from the source array. If no characters
		 *      are provided between the brackets, the original array source is
		 *      returned.
		 *    * `()` - Function notation. Adding `()` to the end of a parameter will
		 *      execute a function of the name given. For example: `browser()` for a
		 *      simple function on the data source, `browser.version()` for a
		 *      function in a nested property or even `browser().version` to get an
		 *      object property if the function called returns an object. Note that
		 *      function notation is recommended for use in `render` rather than
		 *      `data` as it is much simpler to use as a renderer.
		 * * `null` - use the original data source for the row rather than plucking
		 *   data directly from it. This action has effects on two other
		 *   initialisation options:
		 *    * `defaultContent` - When null is given as the `data` option and
		 *      `defaultContent` is specified for the column, the value defined by
		 *      `defaultContent` will be used for the cell.
		 *    * `render` - When null is used for the `data` option and the `render`
		 *      option is specified for the column, the whole data source for the
		 *      row is used for the renderer.
		 * * `function` - the function given will be executed whenever DataTables
		 *   needs to set or get the data for a cell in the column. The function
		 *   takes three parameters:
		 *    * Parameters:
		 *      * `{array|object}` The data source for the row
		 *      * `{string}` The type call data requested - this will be 'set' when
		 *        setting data or 'filter', 'display', 'type', 'sort' or undefined
		 *        when gathering data. Note that when `undefined` is given for the
		 *        type DataTables expects to get the raw data for the object back<
		 *      * `{*}` Data to set when the second parameter is 'set'.
		 *    * Return:
		 *      * The return value from the function is not required when 'set' is
		 *        the type of call, but otherwise the return is what will be used
		 *        for the data requested.
		 *
		 * Note that `data` is a getter and setter option. If you just require
		 * formatting of data for output, you will likely want to use `render` which
		 * is simply a getter and thus simpler to use.
		 *
		 * Note that prior to DataTables 1.9.2 `data` was called `mDataProp`. The
		 * name change reflects the flexibility of this property and is consistent
		 * with the naming of mRender. If 'mDataProp' is given, then it will still
		 * be used by DataTables, as it automatically maps the old name to the new
		 * if required.
		 *
		 *  @type string|int|function|null
		 *  @default null <i>Use automatically calculated column index</i>
		 *
		 *  @name DataTable.defaults.column.data
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Read table data from objects
		 *    // JSON structure for each row:
		 *    //   {
		 *    //      "engine": {value},
		 *    //      "browser": {value},
		 *    //      "platform": {value},
		 *    //      "version": {value},
		 *    //      "grade": {value}
		 *    //   }
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "ajaxSource": "sources/objects.txt",
		 *        "columns": [
		 *          { "data": "engine" },
		 *          { "data": "browser" },
		 *          { "data": "platform" },
		 *          { "data": "version" },
		 *          { "data": "grade" }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Read information from deeply nested objects
		 *    // JSON structure for each row:
		 *    //   {
		 *    //      "engine": {value},
		 *    //      "browser": {value},
		 *    //      "platform": {
		 *    //         "inner": {value}
		 *    //      },
		 *    //      "details": [
		 *    //         {value}, {value}
		 *    //      ]
		 *    //   }
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "ajaxSource": "sources/deep.txt",
		 *        "columns": [
		 *          { "data": "engine" },
		 *          { "data": "browser" },
		 *          { "data": "platform.inner" },
		 *          { "data": "platform.details.0" },
		 *          { "data": "platform.details.1" }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using `data` as a function to provide different information for
		 *    // sorting, filtering and display. In this case, currency (price)
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [ {
		 *          "targets": [ 0 ],
		 *          "data": function ( source, type, val ) {
		 *            if (type === 'set') {
		 *              source.price = val;
		 *              // Store the computed dislay and filter values for efficiency
		 *              source.price_display = val=="" ? "" : "$"+numberFormat(val);
		 *              source.price_filter  = val=="" ? "" : "$"+numberFormat(val)+" "+val;
		 *              return;
		 *            }
		 *            else if (type === 'display') {
		 *              return source.price_display;
		 *            }
		 *            else if (type === 'filter') {
		 *              return source.price_filter;
		 *            }
		 *            // 'sort', 'type' and undefined all just use the integer
		 *            return source.price;
		 *          }
		 *        } ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using default content
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [ {
		 *          "targets": [ 0 ],
		 *          "data": null,
		 *          "defaultContent": "Click to edit"
		 *        } ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using array notation - outputting a list from an array
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [ {
		 *          "targets": [ 0 ],
		 *          "data": "name[, ]"
		 *        } ]
		 *      } );
		 *    } );
		 *
		 */
		"mData": null,
	
	
		/**
		 * This property is the rendering partner to `data` and it is suggested that
		 * when you want to manipulate data for display (including filtering,
		 * sorting etc) without altering the underlying data for the table, use this
		 * property. `render` can be considered to be the the read only companion to
		 * `data` which is read / write (then as such more complex). Like `data`
		 * this option can be given in a number of different ways to effect its
		 * behaviour:
		 *
		 * * `integer` - treated as an array index for the data source. This is the
		 *   default that DataTables uses (incrementally increased for each column).
		 * * `string` - read an object property from the data source. There are
		 *   three 'special' options that can be used in the string to alter how
		 *   DataTables reads the data from the source object:
		 *    * `.` - Dotted Javascript notation. Just as you use a `.` in
		 *      Javascript to read from nested objects, so to can the options
		 *      specified in `data`. For example: `browser.version` or
		 *      `browser.name`. If your object parameter name contains a period, use
		 *      `\\` to escape it - i.e. `first\\.name`.
		 *    * `[]` - Array notation. DataTables can automatically combine data
		 *      from and array source, joining the data with the characters provided
		 *      between the two brackets. For example: `name[, ]` would provide a
		 *      comma-space separated list from the source array. If no characters
		 *      are provided between the brackets, the original array source is
		 *      returned.
		 *    * `()` - Function notation. Adding `()` to the end of a parameter will
		 *      execute a function of the name given. For example: `browser()` for a
		 *      simple function on the data source, `browser.version()` for a
		 *      function in a nested property or even `browser().version` to get an
		 *      object property if the function called returns an object.
		 * * `object` - use different data for the different data types requested by
		 *   DataTables ('filter', 'display', 'type' or 'sort'). The property names
		 *   of the object is the data type the property refers to and the value can
		 *   defined using an integer, string or function using the same rules as
		 *   `render` normally does. Note that an `_` option _must_ be specified.
		 *   This is the default value to use if you haven't specified a value for
		 *   the data type requested by DataTables.
		 * * `function` - the function given will be executed whenever DataTables
		 *   needs to set or get the data for a cell in the column. The function
		 *   takes three parameters:
		 *    * Parameters:
		 *      * {array|object} The data source for the row (based on `data`)
		 *      * {string} The type call data requested - this will be 'filter',
		 *        'display', 'type' or 'sort'.
		 *      * {array|object} The full data source for the row (not based on
		 *        `data`)
		 *    * Return:
		 *      * The return value from the function is what will be used for the
		 *        data requested.
		 *
		 *  @type string|int|function|object|null
		 *  @default null Use the data source value.
		 *
		 *  @name DataTable.defaults.column.render
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Create a comma separated list from an array of objects
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "ajaxSource": "sources/deep.txt",
		 *        "columns": [
		 *          { "data": "engine" },
		 *          { "data": "browser" },
		 *          {
		 *            "data": "platform",
		 *            "render": "[, ].name"
		 *          }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Execute a function to obtain data
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [ {
		 *          "targets": [ 0 ],
		 *          "data": null, // Use the full data source object for the renderer's source
		 *          "render": "browserName()"
		 *        } ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // As an object, extracting different data for the different types
		 *    // This would be used with a data source such as:
		 *    //   { "phone": 5552368, "phone_filter": "5552368 555-2368", "phone_display": "555-2368" }
		 *    // Here the `phone` integer is used for sorting and type detection, while `phone_filter`
		 *    // (which has both forms) is used for filtering for if a user inputs either format, while
		 *    // the formatted phone number is the one that is shown in the table.
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [ {
		 *          "targets": [ 0 ],
		 *          "data": null, // Use the full data source object for the renderer's source
		 *          "render": {
		 *            "_": "phone",
		 *            "filter": "phone_filter",
		 *            "display": "phone_display"
		 *          }
		 *        } ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Use as a function to create a link from the data source
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [ {
		 *          "targets": [ 0 ],
		 *          "data": "download_link",
		 *          "render": function ( data, type, full ) {
		 *            return '<a href="'+data+'">Download</a>';
		 *          }
		 *        } ]
		 *      } );
		 *    } );
		 */
		"mRender": null,
	
	
		/**
		 * Change the cell type created for the column - either TD cells or TH cells. This
		 * can be useful as TH cells have semantic meaning in the table body, allowing them
		 * to act as a header for a row (you may wish to add scope='row' to the TH elements).
		 *  @type string
		 *  @default td
		 *
		 *  @name DataTable.defaults.column.cellType
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Make the first column use TH cells
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [ {
		 *          "targets": [ 0 ],
		 *          "cellType": "th"
		 *        } ]
		 *      } );
		 *    } );
		 */
		"sCellType": "td",
	
	
		/**
		 * Class to give to each cell in this column.
		 *  @type string
		 *  @default <i>Empty string</i>
		 *
		 *  @name DataTable.defaults.column.class
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columnDefs`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [
		 *          { "class": "my_class", "targets": [ 0 ] }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          { "class": "my_class" },
		 *          null,
		 *          null,
		 *          null,
		 *          null
		 *        ]
		 *      } );
		 *    } );
		 */
		"sClass": "",
	
		/**
		 * When DataTables calculates the column widths to assign to each column,
		 * it finds the longest string in each column and then constructs a
		 * temporary table and reads the widths from that. The problem with this
		 * is that "mmm" is much wider then "iiii", but the latter is a longer
		 * string - thus the calculation can go wrong (doing it properly and putting
		 * it into an DOM object and measuring that is horribly(!) slow). Thus as
		 * a "work around" we provide this option. It will append its value to the
		 * text that is found to be the longest string for the column - i.e. padding.
		 * Generally you shouldn't need this!
		 *  @type string
		 *  @default <i>Empty string<i>
		 *
		 *  @name DataTable.defaults.column.contentPadding
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          null,
		 *          null,
		 *          null,
		 *          {
		 *            "contentPadding": "mmm"
		 *          }
		 *        ]
		 *      } );
		 *    } );
		 */
		"sContentPadding": "",
	
	
		/**
		 * Allows a default value to be given for a column's data, and will be used
		 * whenever a null data source is encountered (this can be because `data`
		 * is set to null, or because the data source itself is null).
		 *  @type string
		 *  @default null
		 *
		 *  @name DataTable.defaults.column.defaultContent
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columnDefs`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [
		 *          {
		 *            "data": null,
		 *            "defaultContent": "Edit",
		 *            "targets": [ -1 ]
		 *          }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          null,
		 *          null,
		 *          null,
		 *          {
		 *            "data": null,
		 *            "defaultContent": "Edit"
		 *          }
		 *        ]
		 *      } );
		 *    } );
		 */
		"sDefaultContent": null,
	
	
		/**
		 * This parameter is only used in DataTables' server-side processing. It can
		 * be exceptionally useful to know what columns are being displayed on the
		 * client side, and to map these to database fields. When defined, the names
		 * also allow DataTables to reorder information from the server if it comes
		 * back in an unexpected order (i.e. if you switch your columns around on the
		 * client-side, your server-side code does not also need updating).
		 *  @type string
		 *  @default <i>Empty string</i>
		 *
		 *  @name DataTable.defaults.column.name
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columnDefs`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [
		 *          { "name": "engine", "targets": [ 0 ] },
		 *          { "name": "browser", "targets": [ 1 ] },
		 *          { "name": "platform", "targets": [ 2 ] },
		 *          { "name": "version", "targets": [ 3 ] },
		 *          { "name": "grade", "targets": [ 4 ] }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          { "name": "engine" },
		 *          { "name": "browser" },
		 *          { "name": "platform" },
		 *          { "name": "version" },
		 *          { "name": "grade" }
		 *        ]
		 *      } );
		 *    } );
		 */
		"sName": "",
	
	
		/**
		 * Defines a data source type for the ordering which can be used to read
		 * real-time information from the table (updating the internally cached
		 * version) prior to ordering. This allows ordering to occur on user
		 * editable elements such as form inputs.
		 *  @type string
		 *  @default std
		 *
		 *  @name DataTable.defaults.column.orderDataType
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columnDefs`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [
		 *          { "orderDataType": "dom-text", "targets": [ 2, 3 ] },
		 *          { "type": "numeric", "targets": [ 3 ] },
		 *          { "orderDataType": "dom-select", "targets": [ 4 ] },
		 *          { "orderDataType": "dom-checkbox", "targets": [ 5 ] }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          null,
		 *          null,
		 *          { "orderDataType": "dom-text" },
		 *          { "orderDataType": "dom-text", "type": "numeric" },
		 *          { "orderDataType": "dom-select" },
		 *          { "orderDataType": "dom-checkbox" }
		 *        ]
		 *      } );
		 *    } );
		 */
		"sSortDataType": "std",
	
	
		/**
		 * The title of this column.
		 *  @type string
		 *  @default null <i>Derived from the 'TH' value for this column in the
		 *    original HTML table.</i>
		 *
		 *  @name DataTable.defaults.column.title
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columnDefs`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [
		 *          { "title": "My column title", "targets": [ 0 ] }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          { "title": "My column title" },
		 *          null,
		 *          null,
		 *          null,
		 *          null
		 *        ]
		 *      } );
		 *    } );
		 */
		"sTitle": null,
	
	
		/**
		 * The type allows you to specify how the data for this column will be
		 * ordered. Four types (string, numeric, date and html (which will strip
		 * HTML tags before ordering)) are currently available. Note that only date
		 * formats understood by Javascript's Date() object will be accepted as type
		 * date. For example: "Mar 26, 2008 5:03 PM". May take the values: 'string',
		 * 'numeric', 'date' or 'html' (by default). Further types can be adding
		 * through plug-ins.
		 *  @type string
		 *  @default null <i>Auto-detected from raw data</i>
		 *
		 *  @name DataTable.defaults.column.type
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columnDefs`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [
		 *          { "type": "html", "targets": [ 0 ] }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          { "type": "html" },
		 *          null,
		 *          null,
		 *          null,
		 *          null
		 *        ]
		 *      } );
		 *    } );
		 */
		"sType": null,
	
	
		/**
		 * Defining the width of the column, this parameter may take any CSS value
		 * (3em, 20px etc). DataTables applies 'smart' widths to columns which have not
		 * been given a specific width through this interface ensuring that the table
		 * remains readable.
		 *  @type string
		 *  @default null <i>Automatic</i>
		 *
		 *  @name DataTable.defaults.column.width
		 *  @dtopt Columns
		 *
		 *  @example
		 *    // Using `columnDefs`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columnDefs": [
		 *          { "width": "20%", "targets": [ 0 ] }
		 *        ]
		 *      } );
		 *    } );
		 *
		 *  @example
		 *    // Using `columns`
		 *    $(document).ready( function() {
		 *      $('#example').dataTable( {
		 *        "columns": [
		 *          { "width": "20%" },
		 *          null,
		 *          null,
		 *          null,
		 *          null
		 *        ]
		 *      } );
		 *    } );
		 */
		"sWidth": null
	};
	
	_fnHungarianMap( DataTable.defaults.column );
	
	
	
	/**
	 * DataTables settings object - this holds all the information needed for a
	 * given table, including configuration, data and current application of the
	 * table options. DataTables does not have a single instance for each DataTable
	 * with the settings attached to that instance, but rather instances of the
	 * DataTable "class" are created on-the-fly as needed (typically by a
	 * $().dataTable() call) and the settings object is then applied to that
	 * instance.
	 *
	 * Note that this object is related to {@link DataTable.defaults} but this
	 * one is the internal data store for DataTables's cache of columns. It should
	 * NOT be manipulated outside of DataTables. Any configuration should be done
	 * through the initialisation options.
	 *  @namespace
	 *  @todo Really should attach the settings object to individual instances so we
	 *    don't need to create new instances on each $().dataTable() call (if the
	 *    table already exists). It would also save passing oSettings around and
	 *    into every single function. However, this is a very significant
	 *    architecture change for DataTables and will almost certainly break
	 *    backwards compatibility with older installations. This is something that
	 *    will be done in 2.0.
	 */
	DataTable.models.oSettings = {
		/**
		 * Primary features of DataTables and their enablement state.
		 *  @namespace
		 */
		"oFeatures": {
	
			/**
			 * Flag to say if DataTables should automatically try to calculate the
			 * optimum table and columns widths (true) or not (false).
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bAutoWidth": null,
	
			/**
			 * Delay the creation of TR and TD elements until they are actually
			 * needed by a driven page draw. This can give a significant speed
			 * increase for Ajax source and Javascript source data, but makes no
			 * difference at all fro DOM and server-side processing tables.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bDeferRender": null,
	
			/**
			 * Enable filtering on the table or not. Note that if this is disabled
			 * then there is no filtering at all on the table, including fnFilter.
			 * To just remove the filtering input use sDom and remove the 'f' option.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bFilter": null,
	
			/**
			 * Table information element (the 'Showing x of y records' div) enable
			 * flag.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bInfo": null,
	
			/**
			 * Present a user control allowing the end user to change the page size
			 * when pagination is enabled.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bLengthChange": null,
	
			/**
			 * Pagination enabled or not. Note that if this is disabled then length
			 * changing must also be disabled.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bPaginate": null,
	
			/**
			 * Processing indicator enable flag whenever DataTables is enacting a
			 * user request - typically an Ajax request for server-side processing.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bProcessing": null,
	
			/**
			 * Server-side processing enabled flag - when enabled DataTables will
			 * get all data from the server for every draw - there is no filtering,
			 * sorting or paging done on the client-side.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bServerSide": null,
	
			/**
			 * Sorting enablement flag.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bSort": null,
	
			/**
			 * Multi-column sorting
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bSortMulti": null,
	
			/**
			 * Apply a class to the columns which are being sorted to provide a
			 * visual highlight or not. This can slow things down when enabled since
			 * there is a lot of DOM interaction.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bSortClasses": null,
	
			/**
			 * State saving enablement flag.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bStateSave": null
		},
	
	
		/**
		 * Scrolling settings for a table.
		 *  @namespace
		 */
		"oScroll": {
			/**
			 * When the table is shorter in height than sScrollY, collapse the
			 * table container down to the height of the table (when true).
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type boolean
			 */
			"bCollapse": null,
	
			/**
			 * Width of the scrollbar for the web-browser's platform. Calculated
			 * during table initialisation.
			 *  @type int
			 *  @default 0
			 */
			"iBarWidth": 0,
	
			/**
			 * Viewport width for horizontal scrolling. Horizontal scrolling is
			 * disabled if an empty string.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type string
			 */
			"sX": null,
	
			/**
			 * Width to expand the table to when using x-scrolling. Typically you
			 * should not need to use this.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type string
			 *  @deprecated
			 */
			"sXInner": null,
	
			/**
			 * Viewport height for vertical scrolling. Vertical scrolling is disabled
			 * if an empty string.
			 * Note that this parameter will be set by the initialisation routine. To
			 * set a default use {@link DataTable.defaults}.
			 *  @type string
			 */
			"sY": null
		},
	
		/**
		 * Language information for the table.
		 *  @namespace
		 *  @extends DataTable.defaults.oLanguage
		 */
		"oLanguage": {
			/**
			 * Information callback function. See
			 * {@link DataTable.defaults.fnInfoCallback}
			 *  @type function
			 *  @default null
			 */
			"fnInfoCallback": null
		},
	
		/**
		 * Browser support parameters
		 *  @namespace
		 */
		"oBrowser": {
			/**
			 * Indicate if the browser incorrectly calculates width:100% inside a
			 * scrolling element (IE6/7)
			 *  @type boolean
			 *  @default false
			 */
			"bScrollOversize": false,
	
			/**
			 * Determine if the vertical scrollbar is on the right or left of the
			 * scrolling container - needed for rtl language layout, although not
			 * all browsers move the scrollbar (Safari).
			 *  @type boolean
			 *  @default false
			 */
			"bScrollbarLeft": false,
	
			/**
			 * Flag for if `getBoundingClientRect` is fully supported or not
			 *  @type boolean
			 *  @default false
			 */
			"bBounding": false,
	
			/**
			 * Browser scrollbar width
			 *  @type integer
			 *  @default 0
			 */
			"barWidth": 0
		},
	
	
		"ajax": null,
	
	
		/**
		 * Array referencing the nodes which are used for the features. The
		 * parameters of this object match what is allowed by sDom - i.e.
		 *   <ul>
		 *     <li>'l' - Length changing</li>
		 *     <li>'f' - Filtering input</li>
		 *     <li>'t' - The table!</li>
		 *     <li>'i' - Information</li>
		 *     <li>'p' - Pagination</li>
		 *     <li>'r' - pRocessing</li>
		 *   </ul>
		 *  @type array
		 *  @default []
		 */
		"aanFeatures": [],
	
		/**
		 * Store data information - see {@link DataTable.models.oRow} for detailed
		 * information.
		 *  @type array
		 *  @default []
		 */
		"aoData": [],
	
		/**
		 * Array of indexes which are in the current display (after filtering etc)
		 *  @type array
		 *  @default []
		 */
		"aiDisplay": [],
	
		/**
		 * Array of indexes for display - no filtering
		 *  @type array
		 *  @default []
		 */
		"aiDisplayMaster": [],
	
		/**
		 * Map of row ids to data indexes
		 *  @type object
		 *  @default {}
		 */
		"aIds": {},
	
		/**
		 * Store information about each column that is in use
		 *  @type array
		 *  @default []
		 */
		"aoColumns": [],
	
		/**
		 * Store information about the table's header
		 *  @type array
		 *  @default []
		 */
		"aoHeader": [],
	
		/**
		 * Store information about the table's footer
		 *  @type array
		 *  @default []
		 */
		"aoFooter": [],
	
		/**
		 * Store the applied global search information in case we want to force a
		 * research or compare the old search to a new one.
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @namespace
		 *  @extends DataTable.models.oSearch
		 */
		"oPreviousSearch": {},
	
		/**
		 * Store the applied search for each column - see
		 * {@link DataTable.models.oSearch} for the format that is used for the
		 * filtering information for each column.
		 *  @type array
		 *  @default []
		 */
		"aoPreSearchCols": [],
	
		/**
		 * Sorting that is applied to the table. Note that the inner arrays are
		 * used in the following manner:
		 * <ul>
		 *   <li>Index 0 - column number</li>
		 *   <li>Index 1 - current sorting direction</li>
		 * </ul>
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type array
		 *  @todo These inner arrays should really be objects
		 */
		"aaSorting": null,
	
		/**
		 * Sorting that is always applied to the table (i.e. prefixed in front of
		 * aaSorting).
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type array
		 *  @default []
		 */
		"aaSortingFixed": [],
	
		/**
		 * Classes to use for the striping of a table.
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type array
		 *  @default []
		 */
		"asStripeClasses": null,
	
		/**
		 * If restoring a table - we should restore its striping classes as well
		 *  @type array
		 *  @default []
		 */
		"asDestroyStripes": [],
	
		/**
		 * If restoring a table - we should restore its width
		 *  @type int
		 *  @default 0
		 */
		"sDestroyWidth": 0,
	
		/**
		 * Callback functions array for every time a row is inserted (i.e. on a draw).
		 *  @type array
		 *  @default []
		 */
		"aoRowCallback": [],
	
		/**
		 * Callback functions for the header on each draw.
		 *  @type array
		 *  @default []
		 */
		"aoHeaderCallback": [],
	
		/**
		 * Callback function for the footer on each draw.
		 *  @type array
		 *  @default []
		 */
		"aoFooterCallback": [],
	
		/**
		 * Array of callback functions for draw callback functions
		 *  @type array
		 *  @default []
		 */
		"aoDrawCallback": [],
	
		/**
		 * Array of callback functions for row created function
		 *  @type array
		 *  @default []
		 */
		"aoRowCreatedCallback": [],
	
		/**
		 * Callback functions for just before the table is redrawn. A return of
		 * false will be used to cancel the draw.
		 *  @type array
		 *  @default []
		 */
		"aoPreDrawCallback": [],
	
		/**
		 * Callback functions for when the table has been initialised.
		 *  @type array
		 *  @default []
		 */
		"aoInitComplete": [],
	
	
		/**
		 * Callbacks for modifying the settings to be stored for state saving, prior to
		 * saving state.
		 *  @type array
		 *  @default []
		 */
		"aoStateSaveParams": [],
	
		/**
		 * Callbacks for modifying the settings that have been stored for state saving
		 * prior to using the stored values to restore the state.
		 *  @type array
		 *  @default []
		 */
		"aoStateLoadParams": [],
	
		/**
		 * Callbacks for operating on the settings object once the saved state has been
		 * loaded
		 *  @type array
		 *  @default []
		 */
		"aoStateLoaded": [],
	
		/**
		 * Cache the table ID for quick access
		 *  @type string
		 *  @default <i>Empty string</i>
		 */
		"sTableId": "",
	
		/**
		 * The TABLE node for the main table
		 *  @type node
		 *  @default null
		 */
		"nTable": null,
	
		/**
		 * Permanent ref to the thead element
		 *  @type node
		 *  @default null
		 */
		"nTHead": null,
	
		/**
		 * Permanent ref to the tfoot element - if it exists
		 *  @type node
		 *  @default null
		 */
		"nTFoot": null,
	
		/**
		 * Permanent ref to the tbody element
		 *  @type node
		 *  @default null
		 */
		"nTBody": null,
	
		/**
		 * Cache the wrapper node (contains all DataTables controlled elements)
		 *  @type node
		 *  @default null
		 */
		"nTableWrapper": null,
	
		/**
		 * Indicate if when using server-side processing the loading of data
		 * should be deferred until the second draw.
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type boolean
		 *  @default false
		 */
		"bDeferLoading": false,
	
		/**
		 * Indicate if all required information has been read in
		 *  @type boolean
		 *  @default false
		 */
		"bInitialised": false,
	
		/**
		 * Information about open rows. Each object in the array has the parameters
		 * 'nTr' and 'nParent'
		 *  @type array
		 *  @default []
		 */
		"aoOpenRows": [],
	
		/**
		 * Dictate the positioning of DataTables' control elements - see
		 * {@link DataTable.model.oInit.sDom}.
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type string
		 *  @default null
		 */
		"sDom": null,
	
		/**
		 * Search delay (in mS)
		 *  @type integer
		 *  @default null
		 */
		"searchDelay": null,
	
		/**
		 * Which type of pagination should be used.
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type string
		 *  @default two_button
		 */
		"sPaginationType": "two_button",
	
		/**
		 * The state duration (for `stateSave`) in seconds.
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type int
		 *  @default 0
		 */
		"iStateDuration": 0,
	
		/**
		 * Array of callback functions for state saving. Each array element is an
		 * object with the following parameters:
		 *   <ul>
		 *     <li>function:fn - function to call. Takes two parameters, oSettings
		 *       and the JSON string to save that has been thus far created. Returns
		 *       a JSON string to be inserted into a json object
		 *       (i.e. '"param": [ 0, 1, 2]')</li>
		 *     <li>string:sName - name of callback</li>
		 *   </ul>
		 *  @type array
		 *  @default []
		 */
		"aoStateSave": [],
	
		/**
		 * Array of callback functions for state loading. Each array element is an
		 * object with the following parameters:
		 *   <ul>
		 *     <li>function:fn - function to call. Takes two parameters, oSettings
		 *       and the object stored. May return false to cancel state loading</li>
		 *     <li>string:sName - name of callback</li>
		 *   </ul>
		 *  @type array
		 *  @default []
		 */
		"aoStateLoad": [],
	
		/**
		 * State that was saved. Useful for back reference
		 *  @type object
		 *  @default null
		 */
		"oSavedState": null,
	
		/**
		 * State that was loaded. Useful for back reference
		 *  @type object
		 *  @default null
		 */
		"oLoadedState": null,
	
		/**
		 * Source url for AJAX data for the table.
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type string
		 *  @default null
		 */
		"sAjaxSource": null,
	
		/**
		 * Property from a given object from which to read the table data from. This
		 * can be an empty string (when not server-side processing), in which case
		 * it is  assumed an an array is given directly.
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type string
		 */
		"sAjaxDataProp": null,
	
		/**
		 * Note if draw should be blocked while getting data
		 *  @type boolean
		 *  @default true
		 */
		"bAjaxDataGet": true,
	
		/**
		 * The last jQuery XHR object that was used for server-side data gathering.
		 * This can be used for working with the XHR information in one of the
		 * callbacks
		 *  @type object
		 *  @default null
		 */
		"jqXHR": null,
	
		/**
		 * JSON returned from the server in the last Ajax request
		 *  @type object
		 *  @default undefined
		 */
		"json": undefined,
	
		/**
		 * Data submitted as part of the last Ajax request
		 *  @type object
		 *  @default undefined
		 */
		"oAjaxData": undefined,
	
		/**
		 * Function to get the server-side data.
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type function
		 */
		"fnServerData": null,
	
		/**
		 * Functions which are called prior to sending an Ajax request so extra
		 * parameters can easily be sent to the server
		 *  @type array
		 *  @default []
		 */
		"aoServerParams": [],
	
		/**
		 * Send the XHR HTTP method - GET or POST (could be PUT or DELETE if
		 * required).
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type string
		 */
		"sServerMethod": null,
	
		/**
		 * Format numbers for display.
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type function
		 */
		"fnFormatNumber": null,
	
		/**
		 * List of options that can be used for the user selectable length menu.
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type array
		 *  @default []
		 */
		"aLengthMenu": null,
	
		/**
		 * Counter for the draws that the table does. Also used as a tracker for
		 * server-side processing
		 *  @type int
		 *  @default 0
		 */
		"iDraw": 0,
	
		/**
		 * Indicate if a redraw is being done - useful for Ajax
		 *  @type boolean
		 *  @default false
		 */
		"bDrawing": false,
	
		/**
		 * Draw index (iDraw) of the last error when parsing the returned data
		 *  @type int
		 *  @default -1
		 */
		"iDrawError": -1,
	
		/**
		 * Paging display length
		 *  @type int
		 *  @default 10
		 */
		"_iDisplayLength": 10,
	
		/**
		 * Paging start point - aiDisplay index
		 *  @type int
		 *  @default 0
		 */
		"_iDisplayStart": 0,
	
		/**
		 * Server-side processing - number of records in the result set
		 * (i.e. before filtering), Use fnRecordsTotal rather than
		 * this property to get the value of the number of records, regardless of
		 * the server-side processing setting.
		 *  @type int
		 *  @default 0
		 *  @private
		 */
		"_iRecordsTotal": 0,
	
		/**
		 * Server-side processing - number of records in the current display set
		 * (i.e. after filtering). Use fnRecordsDisplay rather than
		 * this property to get the value of the number of records, regardless of
		 * the server-side processing setting.
		 *  @type boolean
		 *  @default 0
		 *  @private
		 */
		"_iRecordsDisplay": 0,
	
		/**
		 * The classes to use for the table
		 *  @type object
		 *  @default {}
		 */
		"oClasses": {},
	
		/**
		 * Flag attached to the settings object so you can check in the draw
		 * callback if filtering has been done in the draw. Deprecated in favour of
		 * events.
		 *  @type boolean
		 *  @default false
		 *  @deprecated
		 */
		"bFiltered": false,
	
		/**
		 * Flag attached to the settings object so you can check in the draw
		 * callback if sorting has been done in the draw. Deprecated in favour of
		 * events.
		 *  @type boolean
		 *  @default false
		 *  @deprecated
		 */
		"bSorted": false,
	
		/**
		 * Indicate that if multiple rows are in the header and there is more than
		 * one unique cell per column, if the top one (true) or bottom one (false)
		 * should be used for sorting / title by DataTables.
		 * Note that this parameter will be set by the initialisation routine. To
		 * set a default use {@link DataTable.defaults}.
		 *  @type boolean
		 */
		"bSortCellsTop": null,
	
		/**
		 * Initialisation object that is used for the table
		 *  @type object
		 *  @default null
		 */
		"oInit": null,
	
		/**
		 * Destroy callback functions - for plug-ins to attach themselves to the
		 * destroy so they can clean up markup and events.
		 *  @type array
		 *  @default []
		 */
		"aoDestroyCallback": [],
	
	
		/**
		 * Get the number of records in the current record set, before filtering
		 *  @type function
		 */
		"fnRecordsTotal": function ()
		{
			return _fnDataSource( this ) == 'ssp' ?
				this._iRecordsTotal * 1 :
				this.aiDisplayMaster.length;
		},
	
		/**
		 * Get the number of records in the current record set, after filtering
		 *  @type function
		 */
		"fnRecordsDisplay": function ()
		{
			return _fnDataSource( this ) == 'ssp' ?
				this._iRecordsDisplay * 1 :
				this.aiDisplay.length;
		},
	
		/**
		 * Get the display end point - aiDisplay index
		 *  @type function
		 */
		"fnDisplayEnd": function ()
		{
			var
				len      = this._iDisplayLength,
				start    = this._iDisplayStart,
				calc     = start + len,
				records  = this.aiDisplay.length,
				features = this.oFeatures,
				paginate = features.bPaginate;
	
			if ( features.bServerSide ) {
				return paginate === false || len === -1 ?
					start + records :
					Math.min( start+len, this._iRecordsDisplay );
			}
			else {
				return ! paginate || calc>records || len===-1 ?
					records :
					calc;
			}
		},
	
		/**
		 * The DataTables object for this table
		 *  @type object
		 *  @default null
		 */
		"oInstance": null,
	
		/**
		 * Unique identifier for each instance of the DataTables object. If there
		 * is an ID on the table node, then it takes that value, otherwise an
		 * incrementing internal counter is used.
		 *  @type string
		 *  @default null
		 */
		"sInstance": null,
	
		/**
		 * tabindex attribute value that is added to DataTables control elements, allowing
		 * keyboard navigation of the table and its controls.
		 */
		"iTabIndex": 0,
	
		/**
		 * DIV container for the footer scrolling table if scrolling
		 */
		"nScrollHead": null,
	
		/**
		 * DIV container for the footer scrolling table if scrolling
		 */
		"nScrollFoot": null,
	
		/**
		 * Last applied sort
		 *  @type array
		 *  @default []
		 */
		"aLastSort": [],
	
		/**
		 * Stored plug-in instances
		 *  @type object
		 *  @default {}
		 */
		"oPlugins": {},
	
		/**
		 * Function used to get a row's id from the row's data
		 *  @type function
		 *  @default null
		 */
		"rowIdFn": null,
	
		/**
		 * Data location where to store a row's id
		 *  @type string
		 *  @default null
		 */
		"rowId": null
	};

	/**
	 * Extension object for DataTables that is used to provide all extension
	 * options.
	 *
	 * Note that the `DataTable.ext` object is available through
	 * `jQuery.fn.dataTable.ext` where it may be accessed and manipulated. It is
	 * also aliased to `jQuery.fn.dataTableExt` for historic reasons.
	 *  @namespace
	 *  @extends DataTable.models.ext
	 */
	
	
	/**
	 * DataTables extensions
	 * 
	 * This namespace acts as a collection area for plug-ins that can be used to
	 * extend DataTables capabilities. Indeed many of the build in methods
	 * use this method to provide their own capabilities (sorting methods for
	 * example).
	 *
	 * Note that this namespace is aliased to `jQuery.fn.dataTableExt` for legacy
	 * reasons
	 *
	 *  @namespace
	 */
	DataTable.ext = _ext = {
		/**
		 * Buttons. For use with the Buttons extension for DataTables. This is
		 * defined here so other extensions can define buttons regardless of load
		 * order. It is _not_ used by DataTables core.
		 *
		 *  @type object
		 *  @default {}
		 */
		buttons: {},
	
	
		/**
		 * Element class names
		 *
		 *  @type object
		 *  @default {}
		 */
		classes: {},
	
	
		/**
		 * DataTables build type (expanded by the download builder)
		 *
		 *  @type string
		 */
		build:"dt/dt-1.10.16/e-1.7.2/b-1.5.1/r-2.2.1",
	
	
		/**
		 * Error reporting.
		 * 
		 * How should DataTables report an error. Can take the value 'alert',
		 * 'throw', 'none' or a function.
		 *
		 *  @type string|function
		 *  @default alert
		 */
		errMode: "alert",
	
	
		/**
		 * Feature plug-ins.
		 * 
		 * This is an array of objects which describe the feature plug-ins that are
		 * available to DataTables. These feature plug-ins are then available for
		 * use through the `dom` initialisation option.
		 * 
		 * Each feature plug-in is described by an object which must have the
		 * following properties:
		 * 
		 * * `fnInit` - function that is used to initialise the plug-in,
		 * * `cFeature` - a character so the feature can be enabled by the `dom`
		 *   instillation option. This is case sensitive.
		 *
		 * The `fnInit` function has the following input parameters:
		 *
		 * 1. `{object}` DataTables settings object: see
		 *    {@link DataTable.models.oSettings}
		 *
		 * And the following return is expected:
		 * 
		 * * {node|null} The element which contains your feature. Note that the
		 *   return may also be void if your plug-in does not require to inject any
		 *   DOM elements into DataTables control (`dom`) - for example this might
		 *   be useful when developing a plug-in which allows table control via
		 *   keyboard entry
		 *
		 *  @type array
		 *
		 *  @example
		 *    $.fn.dataTable.ext.features.push( {
		 *      "fnInit": function( oSettings ) {
		 *        return new TableTools( { "oDTSettings": oSettings } );
		 *      },
		 *      "cFeature": "T"
		 *    } );
		 */
		feature: [],
	
	
		/**
		 * Row searching.
		 * 
		 * This method of searching is complimentary to the default type based
		 * searching, and a lot more comprehensive as it allows you complete control
		 * over the searching logic. Each element in this array is a function
		 * (parameters described below) that is called for every row in the table,
		 * and your logic decides if it should be included in the searching data set
		 * or not.
		 *
		 * Searching functions have the following input parameters:
		 *
		 * 1. `{object}` DataTables settings object: see
		 *    {@link DataTable.models.oSettings}
		 * 2. `{array|object}` Data for the row to be processed (same as the
		 *    original format that was passed in as the data source, or an array
		 *    from a DOM data source
		 * 3. `{int}` Row index ({@link DataTable.models.oSettings.aoData}), which
		 *    can be useful to retrieve the `TR` element if you need DOM interaction.
		 *
		 * And the following return is expected:
		 *
		 * * {boolean} Include the row in the searched result set (true) or not
		 *   (false)
		 *
		 * Note that as with the main search ability in DataTables, technically this
		 * is "filtering", since it is subtractive. However, for consistency in
		 * naming we call it searching here.
		 *
		 *  @type array
		 *  @default []
		 *
		 *  @example
		 *    // The following example shows custom search being applied to the
		 *    // fourth column (i.e. the data[3] index) based on two input values
		 *    // from the end-user, matching the data in a certain range.
		 *    $.fn.dataTable.ext.search.push(
		 *      function( settings, data, dataIndex ) {
		 *        var min = document.getElementById('min').value * 1;
		 *        var max = document.getElementById('max').value * 1;
		 *        var version = data[3] == "-" ? 0 : data[3]*1;
		 *
		 *        if ( min == "" && max == "" ) {
		 *          return true;
		 *        }
		 *        else if ( min == "" && version < max ) {
		 *          return true;
		 *        }
		 *        else if ( min < version && "" == max ) {
		 *          return true;
		 *        }
		 *        else if ( min < version && version < max ) {
		 *          return true;
		 *        }
		 *        return false;
		 *      }
		 *    );
		 */
		search: [],
	
	
		/**
		 * Selector extensions
		 *
		 * The `selector` option can be used to extend the options available for the
		 * selector modifier options (`selector-modifier` object data type) that
		 * each of the three built in selector types offer (row, column and cell +
		 * their plural counterparts). For example the Select extension uses this
		 * mechanism to provide an option to select only rows, columns and cells
		 * that have been marked as selected by the end user (`{selected: true}`),
		 * which can be used in conjunction with the existing built in selector
		 * options.
		 *
		 * Each property is an array to which functions can be pushed. The functions
		 * take three attributes:
		 *
		 * * Settings object for the host table
		 * * Options object (`selector-modifier` object type)
		 * * Array of selected item indexes
		 *
		 * The return is an array of the resulting item indexes after the custom
		 * selector has been applied.
		 *
		 *  @type object
		 */
		selector: {
			cell: [],
			column: [],
			row: []
		},
	
	
		/**
		 * Internal functions, exposed for used in plug-ins.
		 * 
		 * Please note that you should not need to use the internal methods for
		 * anything other than a plug-in (and even then, try to avoid if possible).
		 * The internal function may change between releases.
		 *
		 *  @type object
		 *  @default {}
		 */
		internal: {},
	
	
		/**
		 * Legacy configuration options. Enable and disable legacy options that
		 * are available in DataTables.
		 *
		 *  @type object
		 */
		legacy: {
			/**
			 * Enable / disable DataTables 1.9 compatible server-side processing
			 * requests
			 *
			 *  @type boolean
			 *  @default null
			 */
			ajax: null
		},
	
	
		/**
		 * Pagination plug-in methods.
		 * 
		 * Each entry in this object is a function and defines which buttons should
		 * be shown by the pagination rendering method that is used for the table:
		 * {@link DataTable.ext.renderer.pageButton}. The renderer addresses how the
		 * buttons are displayed in the document, while the functions here tell it
		 * what buttons to display. This is done by returning an array of button
		 * descriptions (what each button will do).
		 *
		 * Pagination types (the four built in options and any additional plug-in
		 * options defined here) can be used through the `paginationType`
		 * initialisation parameter.
		 *
		 * The functions defined take two parameters:
		 *
		 * 1. `{int} page` The current page index
		 * 2. `{int} pages` The number of pages in the table
		 *
		 * Each function is expected to return an array where each element of the
		 * array can be one of:
		 *
		 * * `first` - Jump to first page when activated
		 * * `last` - Jump to last page when activated
		 * * `previous` - Show previous page when activated
		 * * `next` - Show next page when activated
		 * * `{int}` - Show page of the index given
		 * * `{array}` - A nested array containing the above elements to add a
		 *   containing 'DIV' element (might be useful for styling).
		 *
		 * Note that DataTables v1.9- used this object slightly differently whereby
		 * an object with two functions would be defined for each plug-in. That
		 * ability is still supported by DataTables 1.10+ to provide backwards
		 * compatibility, but this option of use is now decremented and no longer
		 * documented in DataTables 1.10+.
		 *
		 *  @type object
		 *  @default {}
		 *
		 *  @example
		 *    // Show previous, next and current page buttons only
		 *    $.fn.dataTableExt.oPagination.current = function ( page, pages ) {
		 *      return [ 'previous', page, 'next' ];
		 *    };
		 */
		pager: {},
	
	
		renderer: {
			pageButton: {},
			header: {}
		},
	
	
		/**
		 * Ordering plug-ins - custom data source
		 * 
		 * The extension options for ordering of data available here is complimentary
		 * to the default type based ordering that DataTables typically uses. It
		 * allows much greater control over the the data that is being used to
		 * order a column, but is necessarily therefore more complex.
		 * 
		 * This type of ordering is useful if you want to do ordering based on data
		 * live from the DOM (for example the contents of an 'input' element) rather
		 * than just the static string that DataTables knows of.
		 * 
		 * The way these plug-ins work is that you create an array of the values you
		 * wish to be ordering for the column in question and then return that
		 * array. The data in the array much be in the index order of the rows in
		 * the table (not the currently ordering order!). Which order data gathering
		 * function is run here depends on the `dt-init columns.orderDataType`
		 * parameter that is used for the column (if any).
		 *
		 * The functions defined take two parameters:
		 *
		 * 1. `{object}` DataTables settings object: see
		 *    {@link DataTable.models.oSettings}
		 * 2. `{int}` Target column index
		 *
		 * Each function is expected to return an array:
		 *
		 * * `{array}` Data for the column to be ordering upon
		 *
		 *  @type array
		 *
		 *  @example
		 *    // Ordering using `input` node values
		 *    $.fn.dataTable.ext.order['dom-text'] = function  ( settings, col )
		 *    {
		 *      return this.api().column( col, {order:'index'} ).nodes().map( function ( td, i ) {
		 *        return $('input', td).val();
		 *      } );
		 *    }
		 */
		order: {},
	
	
		/**
		 * Type based plug-ins.
		 *
		 * Each column in DataTables has a type assigned to it, either by automatic
		 * detection or by direct assignment using the `type` option for the column.
		 * The type of a column will effect how it is ordering and search (plug-ins
		 * can also make use of the column type if required).
		 *
		 * @namespace
		 */
		type: {
			/**
			 * Type detection functions.
			 *
			 * The functions defined in this object are used to automatically detect
			 * a column's type, making initialisation of DataTables super easy, even
			 * when complex data is in the table.
			 *
			 * The functions defined take two parameters:
			 *
		     *  1. `{*}` Data from the column cell to be analysed
		     *  2. `{settings}` DataTables settings object. This can be used to
		     *     perform context specific type detection - for example detection
		     *     based on language settings such as using a comma for a decimal
		     *     place. Generally speaking the options from the settings will not
		     *     be required
			 *
			 * Each function is expected to return:
			 *
			 * * `{string|null}` Data type detected, or null if unknown (and thus
			 *   pass it on to the other type detection functions.
			 *
			 *  @type array
			 *
			 *  @example
			 *    // Currency type detection plug-in:
			 *    $.fn.dataTable.ext.type.detect.push(
			 *      function ( data, settings ) {
			 *        // Check the numeric part
			 *        if ( ! $.isNumeric( data.substring(1) ) ) {
			 *          return null;
			 *        }
			 *
			 *        // Check prefixed by currency
			 *        if ( data.charAt(0) == '$' || data.charAt(0) == '&pound;' ) {
			 *          return 'currency';
			 *        }
			 *        return null;
			 *      }
			 *    );
			 */
			detect: [],
	
	
			/**
			 * Type based search formatting.
			 *
			 * The type based searching functions can be used to pre-format the
			 * data to be search on. For example, it can be used to strip HTML
			 * tags or to de-format telephone numbers for numeric only searching.
			 *
			 * Note that is a search is not defined for a column of a given type,
			 * no search formatting will be performed.
			 * 
			 * Pre-processing of searching data plug-ins - When you assign the sType
			 * for a column (or have it automatically detected for you by DataTables
			 * or a type detection plug-in), you will typically be using this for
			 * custom sorting, but it can also be used to provide custom searching
			 * by allowing you to pre-processing the data and returning the data in
			 * the format that should be searched upon. This is done by adding
			 * functions this object with a parameter name which matches the sType
			 * for that target column. This is the corollary of <i>afnSortData</i>
			 * for searching data.
			 *
			 * The functions defined take a single parameter:
			 *
		     *  1. `{*}` Data from the column cell to be prepared for searching
			 *
			 * Each function is expected to return:
			 *
			 * * `{string|null}` Formatted string that will be used for the searching.
			 *
			 *  @type object
			 *  @default {}
			 *
			 *  @example
			 *    $.fn.dataTable.ext.type.search['title-numeric'] = function ( d ) {
			 *      return d.replace(/\n/g," ").replace( /<.*?>/g, "" );
			 *    }
			 */
			search: {},
	
	
			/**
			 * Type based ordering.
			 *
			 * The column type tells DataTables what ordering to apply to the table
			 * when a column is sorted upon. The order for each type that is defined,
			 * is defined by the functions available in this object.
			 *
			 * Each ordering option can be described by three properties added to
			 * this object:
			 *
			 * * `{type}-pre` - Pre-formatting function
			 * * `{type}-asc` - Ascending order function
			 * * `{type}-desc` - Descending order function
			 *
			 * All three can be used together, only `{type}-pre` or only
			 * `{type}-asc` and `{type}-desc` together. It is generally recommended
			 * that only `{type}-pre` is used, as this provides the optimal
			 * implementation in terms of speed, although the others are provided
			 * for compatibility with existing Javascript sort functions.
			 *
			 * `{type}-pre`: Functions defined take a single parameter:
			 *
		     *  1. `{*}` Data from the column cell to be prepared for ordering
			 *
			 * And return:
			 *
			 * * `{*}` Data to be sorted upon
			 *
			 * `{type}-asc` and `{type}-desc`: Functions are typical Javascript sort
			 * functions, taking two parameters:
			 *
		     *  1. `{*}` Data to compare to the second parameter
		     *  2. `{*}` Data to compare to the first parameter
			 *
			 * And returning:
			 *
			 * * `{*}` Ordering match: <0 if first parameter should be sorted lower
			 *   than the second parameter, ===0 if the two parameters are equal and
			 *   >0 if the first parameter should be sorted height than the second
			 *   parameter.
			 * 
			 *  @type object
			 *  @default {}
			 *
			 *  @example
			 *    // Numeric ordering of formatted numbers with a pre-formatter
			 *    $.extend( $.fn.dataTable.ext.type.order, {
			 *      "string-pre": function(x) {
			 *        a = (a === "-" || a === "") ? 0 : a.replace( /[^\d\-\.]/g, "" );
			 *        return parseFloat( a );
			 *      }
			 *    } );
			 *
			 *  @example
			 *    // Case-sensitive string ordering, with no pre-formatting method
			 *    $.extend( $.fn.dataTable.ext.order, {
			 *      "string-case-asc": function(x,y) {
			 *        return ((x < y) ? -1 : ((x > y) ? 1 : 0));
			 *      },
			 *      "string-case-desc": function(x,y) {
			 *        return ((x < y) ? 1 : ((x > y) ? -1 : 0));
			 *      }
			 *    } );
			 */
			order: {}
		},
	
		/**
		 * Unique DataTables instance counter
		 *
		 * @type int
		 * @private
		 */
		_unique: 0,
	
	
		//
		// Depreciated
		// The following properties are retained for backwards compatiblity only.
		// The should not be used in new projects and will be removed in a future
		// version
		//
	
		/**
		 * Version check function.
		 *  @type function
		 *  @depreciated Since 1.10
		 */
		fnVersionCheck: DataTable.fnVersionCheck,
	
	
		/**
		 * Index for what 'this' index API functions should use
		 *  @type int
		 *  @deprecated Since v1.10
		 */
		iApiIndex: 0,
	
	
		/**
		 * jQuery UI class container
		 *  @type object
		 *  @deprecated Since v1.10
		 */
		oJUIClasses: {},
	
	
		/**
		 * Software version
		 *  @type string
		 *  @deprecated Since v1.10
		 */
		sVersion: DataTable.version
	};
	
	
	//
	// Backwards compatibility. Alias to pre 1.10 Hungarian notation counter parts
	//
	$.extend( _ext, {
		afnFiltering: _ext.search,
		aTypes:       _ext.type.detect,
		ofnSearch:    _ext.type.search,
		oSort:        _ext.type.order,
		afnSortData:  _ext.order,
		aoFeatures:   _ext.feature,
		oApi:         _ext.internal,
		oStdClasses:  _ext.classes,
		oPagination:  _ext.pager
	} );
	
	
	$.extend( DataTable.ext.classes, {
		"sTable": "dataTable",
		"sNoFooter": "no-footer",
	
		/* Paging buttons */
		"sPageButton": "paginate_button",
		"sPageButtonActive": "current",
		"sPageButtonDisabled": "disabled",
	
		/* Striping classes */
		"sStripeOdd": "odd",
		"sStripeEven": "even",
	
		/* Empty row */
		"sRowEmpty": "dataTables_empty",
	
		/* Features */
		"sWrapper": "dataTables_wrapper",
		"sFilter": "dataTables_filter",
		"sInfo": "dataTables_info",
		"sPaging": "dataTables_paginate paging_", /* Note that the type is postfixed */
		"sLength": "dataTables_length",
		"sProcessing": "dataTables_processing",
	
		/* Sorting */
		"sSortAsc": "sorting_asc",
		"sSortDesc": "sorting_desc",
		"sSortable": "sorting", /* Sortable in both directions */
		"sSortableAsc": "sorting_asc_disabled",
		"sSortableDesc": "sorting_desc_disabled",
		"sSortableNone": "sorting_disabled",
		"sSortColumn": "sorting_", /* Note that an int is postfixed for the sorting order */
	
		/* Filtering */
		"sFilterInput": "",
	
		/* Page length */
		"sLengthSelect": "",
	
		/* Scrolling */
		"sScrollWrapper": "dataTables_scroll",
		"sScrollHead": "dataTables_scrollHead",
		"sScrollHeadInner": "dataTables_scrollHeadInner",
		"sScrollBody": "dataTables_scrollBody",
		"sScrollFoot": "dataTables_scrollFoot",
		"sScrollFootInner": "dataTables_scrollFootInner",
	
		/* Misc */
		"sHeaderTH": "",
		"sFooterTH": "",
	
		// Deprecated
		"sSortJUIAsc": "",
		"sSortJUIDesc": "",
		"sSortJUI": "",
		"sSortJUIAscAllowed": "",
		"sSortJUIDescAllowed": "",
		"sSortJUIWrapper": "",
		"sSortIcon": "",
		"sJUIHeader": "",
		"sJUIFooter": ""
	} );
	
	
	var extPagination = DataTable.ext.pager;
	
	function _numbers ( page, pages ) {
		var
			numbers = [],
			buttons = extPagination.numbers_length,
			half = Math.floor( buttons / 2 ),
			i = 1;
	
		if ( pages <= buttons ) {
			numbers = _range( 0, pages );
		}
		else if ( page <= half ) {
			numbers = _range( 0, buttons-2 );
			numbers.push( 'ellipsis' );
			numbers.push( pages-1 );
		}
		else if ( page >= pages - 1 - half ) {
			numbers = _range( pages-(buttons-2), pages );
			numbers.splice( 0, 0, 'ellipsis' ); // no unshift in ie6
			numbers.splice( 0, 0, 0 );
		}
		else {
			numbers = _range( page-half+2, page+half-1 );
			numbers.push( 'ellipsis' );
			numbers.push( pages-1 );
			numbers.splice( 0, 0, 'ellipsis' );
			numbers.splice( 0, 0, 0 );
		}
	
		numbers.DT_el = 'span';
		return numbers;
	}
	
	
	$.extend( extPagination, {
		simple: function ( page, pages ) {
			return [ 'previous', 'next' ];
		},
	
		full: function ( page, pages ) {
			return [  'first', 'previous', 'next', 'last' ];
		},
	
		numbers: function ( page, pages ) {
			return [ _numbers(page, pages) ];
		},
	
		simple_numbers: function ( page, pages ) {
			return [ 'previous', _numbers(page, pages), 'next' ];
		},
	
		full_numbers: function ( page, pages ) {
			return [ 'first', 'previous', _numbers(page, pages), 'next', 'last' ];
		},
		
		first_last_numbers: function (page, pages) {
	 		return ['first', _numbers(page, pages), 'last'];
	 	},
	
		// For testing and plug-ins to use
		_numbers: _numbers,
	
		// Number of number buttons (including ellipsis) to show. _Must be odd!_
		numbers_length: 7
	} );
	
	
	$.extend( true, DataTable.ext.renderer, {
		pageButton: {
			_: function ( settings, host, idx, buttons, page, pages ) {
				var classes = settings.oClasses;
				var lang = settings.oLanguage.oPaginate;
				var aria = settings.oLanguage.oAria.paginate || {};
				var btnDisplay, btnClass, counter=0;
	
				var attach = function( container, buttons ) {
					var i, ien, node, button;
					var clickHandler = function ( e ) {
						_fnPageChange( settings, e.data.action, true );
					};
	
					for ( i=0, ien=buttons.length ; i<ien ; i++ ) {
						button = buttons[i];
	
						if ( $.isArray( button ) ) {
							var inner = $( '<'+(button.DT_el || 'div')+'/>' )
								.appendTo( container );
							attach( inner, button );
						}
						else {
							btnDisplay = null;
							btnClass = '';
	
							switch ( button ) {
								case 'ellipsis':
									container.append('<span class="ellipsis">&#x2026;</span>');
									break;
	
								case 'first':
									btnDisplay = lang.sFirst;
									btnClass = button + (page > 0 ?
										'' : ' '+classes.sPageButtonDisabled);
									break;
	
								case 'previous':
									btnDisplay = lang.sPrevious;
									btnClass = button + (page > 0 ?
										'' : ' '+classes.sPageButtonDisabled);
									break;
	
								case 'next':
									btnDisplay = lang.sNext;
									btnClass = button + (page < pages-1 ?
										'' : ' '+classes.sPageButtonDisabled);
									break;
	
								case 'last':
									btnDisplay = lang.sLast;
									btnClass = button + (page < pages-1 ?
										'' : ' '+classes.sPageButtonDisabled);
									break;
	
								default:
									btnDisplay = button + 1;
									btnClass = page === button ?
										classes.sPageButtonActive : '';
									break;
							}
	
							if ( btnDisplay !== null ) {
								node = $('<a>', {
										'class': classes.sPageButton+' '+btnClass,
										'aria-controls': settings.sTableId,
										'aria-label': aria[ button ],
										'data-dt-idx': counter,
										'tabindex': settings.iTabIndex,
										'id': idx === 0 && typeof button === 'string' ?
											settings.sTableId +'_'+ button :
											null
									} )
									.html( btnDisplay )
									.appendTo( container );
	
								_fnBindAction(
									node, {action: button}, clickHandler
								);
	
								counter++;
							}
						}
					}
				};
	
				// IE9 throws an 'unknown error' if document.activeElement is used
				// inside an iframe or frame. Try / catch the error. Not good for
				// accessibility, but neither are frames.
				var activeEl;
	
				try {
					// Because this approach is destroying and recreating the paging
					// elements, focus is lost on the select button which is bad for
					// accessibility. So we want to restore focus once the draw has
					// completed
					activeEl = $(host).find(document.activeElement).data('dt-idx');
				}
				catch (e) {}
	
				attach( $(host).empty(), buttons );
	
				if ( activeEl !== undefined ) {
					$(host).find( '[data-dt-idx='+activeEl+']' ).focus();
				}
			}
		}
	} );
	
	
	
	// Built in type detection. See model.ext.aTypes for information about
	// what is required from this methods.
	$.extend( DataTable.ext.type.detect, [
		// Plain numbers - first since V8 detects some plain numbers as dates
		// e.g. Date.parse('55') (but not all, e.g. Date.parse('22')...).
		function ( d, settings )
		{
			var decimal = settings.oLanguage.sDecimal;
			return _isNumber( d, decimal ) ? 'num'+decimal : null;
		},
	
		// Dates (only those recognised by the browser's Date.parse)
		function ( d, settings )
		{
			// V8 tries _very_ hard to make a string passed into `Date.parse()`
			// valid, so we need to use a regex to restrict date formats. Use a
			// plug-in for anything other than ISO8601 style strings
			if ( d && !(d instanceof Date) && ! _re_date.test(d) ) {
				return null;
			}
			var parsed = Date.parse(d);
			return (parsed !== null && !isNaN(parsed)) || _empty(d) ? 'date' : null;
		},
	
		// Formatted numbers
		function ( d, settings )
		{
			var decimal = settings.oLanguage.sDecimal;
			return _isNumber( d, decimal, true ) ? 'num-fmt'+decimal : null;
		},
	
		// HTML numeric
		function ( d, settings )
		{
			var decimal = settings.oLanguage.sDecimal;
			return _htmlNumeric( d, decimal ) ? 'html-num'+decimal : null;
		},
	
		// HTML numeric, formatted
		function ( d, settings )
		{
			var decimal = settings.oLanguage.sDecimal;
			return _htmlNumeric( d, decimal, true ) ? 'html-num-fmt'+decimal : null;
		},
	
		// HTML (this is strict checking - there must be html)
		function ( d, settings )
		{
			return _empty( d ) || (typeof d === 'string' && d.indexOf('<') !== -1) ?
				'html' : null;
		}
	] );
	
	
	
	// Filter formatting functions. See model.ext.ofnSearch for information about
	// what is required from these methods.
	// 
	// Note that additional search methods are added for the html numbers and
	// html formatted numbers by `_addNumericSort()` when we know what the decimal
	// place is
	
	
	$.extend( DataTable.ext.type.search, {
		html: function ( data ) {
			return _empty(data) ?
				data :
				typeof data === 'string' ?
					data
						.replace( _re_new_lines, " " )
						.replace( _re_html, "" ) :
					'';
		},
	
		string: function ( data ) {
			return _empty(data) ?
				data :
				typeof data === 'string' ?
					data.replace( _re_new_lines, " " ) :
					data;
		}
	} );
	
	
	
	var __numericReplace = function ( d, decimalPlace, re1, re2 ) {
		if ( d !== 0 && (!d || d === '-') ) {
			return -Infinity;
		}
	
		// If a decimal place other than `.` is used, it needs to be given to the
		// function so we can detect it and replace with a `.` which is the only
		// decimal place Javascript recognises - it is not locale aware.
		if ( decimalPlace ) {
			d = _numToDecimal( d, decimalPlace );
		}
	
		if ( d.replace ) {
			if ( re1 ) {
				d = d.replace( re1, '' );
			}
	
			if ( re2 ) {
				d = d.replace( re2, '' );
			}
		}
	
		return d * 1;
	};
	
	
	// Add the numeric 'deformatting' functions for sorting and search. This is done
	// in a function to provide an easy ability for the language options to add
	// additional methods if a non-period decimal place is used.
	function _addNumericSort ( decimalPlace ) {
		$.each(
			{
				// Plain numbers
				"num": function ( d ) {
					return __numericReplace( d, decimalPlace );
				},
	
				// Formatted numbers
				"num-fmt": function ( d ) {
					return __numericReplace( d, decimalPlace, _re_formatted_numeric );
				},
	
				// HTML numeric
				"html-num": function ( d ) {
					return __numericReplace( d, decimalPlace, _re_html );
				},
	
				// HTML numeric, formatted
				"html-num-fmt": function ( d ) {
					return __numericReplace( d, decimalPlace, _re_html, _re_formatted_numeric );
				}
			},
			function ( key, fn ) {
				// Add the ordering method
				_ext.type.order[ key+decimalPlace+'-pre' ] = fn;
	
				// For HTML types add a search formatter that will strip the HTML
				if ( key.match(/^html\-/) ) {
					_ext.type.search[ key+decimalPlace ] = _ext.type.search.html;
				}
			}
		);
	}
	
	
	// Default sort methods
	$.extend( _ext.type.order, {
		// Dates
		"date-pre": function ( d ) {
			return Date.parse( d ) || -Infinity;
		},
	
		// html
		"html-pre": function ( a ) {
			return _empty(a) ?
				'' :
				a.replace ?
					a.replace( /<.*?>/g, "" ).toLowerCase() :
					a+'';
		},
	
		// string
		"string-pre": function ( a ) {
			// This is a little complex, but faster than always calling toString,
			// http://jsperf.com/tostring-v-check
			return _empty(a) ?
				'' :
				typeof a === 'string' ?
					a.toLowerCase() :
					! a.toString ?
						'' :
						a.toString();
		},
	
		// string-asc and -desc are retained only for compatibility with the old
		// sort methods
		"string-asc": function ( x, y ) {
			return ((x < y) ? -1 : ((x > y) ? 1 : 0));
		},
	
		"string-desc": function ( x, y ) {
			return ((x < y) ? 1 : ((x > y) ? -1 : 0));
		}
	} );
	
	
	// Numeric sorting types - order doesn't matter here
	_addNumericSort( '' );
	
	
	$.extend( true, DataTable.ext.renderer, {
		header: {
			_: function ( settings, cell, column, classes ) {
				// No additional mark-up required
				// Attach a sort listener to update on sort - note that using the
				// `DT` namespace will allow the event to be removed automatically
				// on destroy, while the `dt` namespaced event is the one we are
				// listening for
				$(settings.nTable).on( 'order.dt.DT', function ( e, ctx, sorting, columns ) {
					if ( settings !== ctx ) { // need to check this this is the host
						return;               // table, not a nested one
					}
	
					var colIdx = column.idx;
	
					cell
						.removeClass(
							column.sSortingClass +' '+
							classes.sSortAsc +' '+
							classes.sSortDesc
						)
						.addClass( columns[ colIdx ] == 'asc' ?
							classes.sSortAsc : columns[ colIdx ] == 'desc' ?
								classes.sSortDesc :
								column.sSortingClass
						);
				} );
			},
	
			jqueryui: function ( settings, cell, column, classes ) {
				$('<div/>')
					.addClass( classes.sSortJUIWrapper )
					.append( cell.contents() )
					.append( $('<span/>')
						.addClass( classes.sSortIcon+' '+column.sSortingClassJUI )
					)
					.appendTo( cell );
	
				// Attach a sort listener to update on sort
				$(settings.nTable).on( 'order.dt.DT', function ( e, ctx, sorting, columns ) {
					if ( settings !== ctx ) {
						return;
					}
	
					var colIdx = column.idx;
	
					cell
						.removeClass( classes.sSortAsc +" "+classes.sSortDesc )
						.addClass( columns[ colIdx ] == 'asc' ?
							classes.sSortAsc : columns[ colIdx ] == 'desc' ?
								classes.sSortDesc :
								column.sSortingClass
						);
	
					cell
						.find( 'span.'+classes.sSortIcon )
						.removeClass(
							classes.sSortJUIAsc +" "+
							classes.sSortJUIDesc +" "+
							classes.sSortJUI +" "+
							classes.sSortJUIAscAllowed +" "+
							classes.sSortJUIDescAllowed
						)
						.addClass( columns[ colIdx ] == 'asc' ?
							classes.sSortJUIAsc : columns[ colIdx ] == 'desc' ?
								classes.sSortJUIDesc :
								column.sSortingClassJUI
						);
				} );
			}
		}
	} );
	
	/*
	 * Public helper functions. These aren't used internally by DataTables, or
	 * called by any of the options passed into DataTables, but they can be used
	 * externally by developers working with DataTables. They are helper functions
	 * to make working with DataTables a little bit easier.
	 */
	
	var __htmlEscapeEntities = function ( d ) {
		return typeof d === 'string' ?
			d.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') :
			d;
	};
	
	/**
	 * Helpers for `columns.render`.
	 *
	 * The options defined here can be used with the `columns.render` initialisation
	 * option to provide a display renderer. The following functions are defined:
	 *
	 * * `number` - Will format numeric data (defined by `columns.data`) for
	 *   display, retaining the original unformatted data for sorting and filtering.
	 *   It takes 5 parameters:
	 *   * `string` - Thousands grouping separator
	 *   * `string` - Decimal point indicator
	 *   * `integer` - Number of decimal points to show
	 *   * `string` (optional) - Prefix.
	 *   * `string` (optional) - Postfix (/suffix).
	 * * `text` - Escape HTML to help prevent XSS attacks. It has no optional
	 *   parameters.
	 *
	 * @example
	 *   // Column definition using the number renderer
	 *   {
	 *     data: "salary",
	 *     render: $.fn.dataTable.render.number( '\'', '.', 0, '$' )
	 *   }
	 *
	 * @namespace
	 */
	DataTable.render = {
		number: function ( thousands, decimal, precision, prefix, postfix ) {
			return {
				display: function ( d ) {
					if ( typeof d !== 'number' && typeof d !== 'string' ) {
						return d;
					}
	
					var negative = d < 0 ? '-' : '';
					var flo = parseFloat( d );
	
					// If NaN then there isn't much formatting that we can do - just
					// return immediately, escaping any HTML (this was supposed to
					// be a number after all)
					if ( isNaN( flo ) ) {
						return __htmlEscapeEntities( d );
					}
	
					flo = flo.toFixed( precision );
					d = Math.abs( flo );
	
					var intPart = parseInt( d, 10 );
					var floatPart = precision ?
						decimal+(d - intPart).toFixed( precision ).substring( 2 ):
						'';
	
					return negative + (prefix||'') +
						intPart.toString().replace(
							/\B(?=(\d{3})+(?!\d))/g, thousands
						) +
						floatPart +
						(postfix||'');
				}
			};
		},
	
		text: function () {
			return {
				display: __htmlEscapeEntities
			};
		}
	};
	
	
	/*
	 * This is really a good bit rubbish this method of exposing the internal methods
	 * publicly... - To be fixed in 2.0 using methods on the prototype
	 */
	
	
	/**
	 * Create a wrapper function for exporting an internal functions to an external API.
	 *  @param {string} fn API function name
	 *  @returns {function} wrapped function
	 *  @memberof DataTable#internal
	 */
	function _fnExternApiFunc (fn)
	{
		return function() {
			var args = [_fnSettingsFromNode( this[DataTable.ext.iApiIndex] )].concat(
				Array.prototype.slice.call(arguments)
			);
			return DataTable.ext.internal[fn].apply( this, args );
		};
	}
	
	
	/**
	 * Reference to internal functions for use by plug-in developers. Note that
	 * these methods are references to internal functions and are considered to be
	 * private. If you use these methods, be aware that they are liable to change
	 * between versions.
	 *  @namespace
	 */
	$.extend( DataTable.ext.internal, {
		_fnExternApiFunc: _fnExternApiFunc,
		_fnBuildAjax: _fnBuildAjax,
		_fnAjaxUpdate: _fnAjaxUpdate,
		_fnAjaxParameters: _fnAjaxParameters,
		_fnAjaxUpdateDraw: _fnAjaxUpdateDraw,
		_fnAjaxDataSrc: _fnAjaxDataSrc,
		_fnAddColumn: _fnAddColumn,
		_fnColumnOptions: _fnColumnOptions,
		_fnAdjustColumnSizing: _fnAdjustColumnSizing,
		_fnVisibleToColumnIndex: _fnVisibleToColumnIndex,
		_fnColumnIndexToVisible: _fnColumnIndexToVisible,
		_fnVisbleColumns: _fnVisbleColumns,
		_fnGetColumns: _fnGetColumns,
		_fnColumnTypes: _fnColumnTypes,
		_fnApplyColumnDefs: _fnApplyColumnDefs,
		_fnHungarianMap: _fnHungarianMap,
		_fnCamelToHungarian: _fnCamelToHungarian,
		_fnLanguageCompat: _fnLanguageCompat,
		_fnBrowserDetect: _fnBrowserDetect,
		_fnAddData: _fnAddData,
		_fnAddTr: _fnAddTr,
		_fnNodeToDataIndex: _fnNodeToDataIndex,
		_fnNodeToColumnIndex: _fnNodeToColumnIndex,
		_fnGetCellData: _fnGetCellData,
		_fnSetCellData: _fnSetCellData,
		_fnSplitObjNotation: _fnSplitObjNotation,
		_fnGetObjectDataFn: _fnGetObjectDataFn,
		_fnSetObjectDataFn: _fnSetObjectDataFn,
		_fnGetDataMaster: _fnGetDataMaster,
		_fnClearTable: _fnClearTable,
		_fnDeleteIndex: _fnDeleteIndex,
		_fnInvalidate: _fnInvalidate,
		_fnGetRowElements: _fnGetRowElements,
		_fnCreateTr: _fnCreateTr,
		_fnBuildHead: _fnBuildHead,
		_fnDrawHead: _fnDrawHead,
		_fnDraw: _fnDraw,
		_fnReDraw: _fnReDraw,
		_fnAddOptionsHtml: _fnAddOptionsHtml,
		_fnDetectHeader: _fnDetectHeader,
		_fnGetUniqueThs: _fnGetUniqueThs,
		_fnFeatureHtmlFilter: _fnFeatureHtmlFilter,
		_fnFilterComplete: _fnFilterComplete,
		_fnFilterCustom: _fnFilterCustom,
		_fnFilterColumn: _fnFilterColumn,
		_fnFilter: _fnFilter,
		_fnFilterCreateSearch: _fnFilterCreateSearch,
		_fnEscapeRegex: _fnEscapeRegex,
		_fnFilterData: _fnFilterData,
		_fnFeatureHtmlInfo: _fnFeatureHtmlInfo,
		_fnUpdateInfo: _fnUpdateInfo,
		_fnInfoMacros: _fnInfoMacros,
		_fnInitialise: _fnInitialise,
		_fnInitComplete: _fnInitComplete,
		_fnLengthChange: _fnLengthChange,
		_fnFeatureHtmlLength: _fnFeatureHtmlLength,
		_fnFeatureHtmlPaginate: _fnFeatureHtmlPaginate,
		_fnPageChange: _fnPageChange,
		_fnFeatureHtmlProcessing: _fnFeatureHtmlProcessing,
		_fnProcessingDisplay: _fnProcessingDisplay,
		_fnFeatureHtmlTable: _fnFeatureHtmlTable,
		_fnScrollDraw: _fnScrollDraw,
		_fnApplyToChildren: _fnApplyToChildren,
		_fnCalculateColumnWidths: _fnCalculateColumnWidths,
		_fnThrottle: _fnThrottle,
		_fnConvertToWidth: _fnConvertToWidth,
		_fnGetWidestNode: _fnGetWidestNode,
		_fnGetMaxLenString: _fnGetMaxLenString,
		_fnStringToCss: _fnStringToCss,
		_fnSortFlatten: _fnSortFlatten,
		_fnSort: _fnSort,
		_fnSortAria: _fnSortAria,
		_fnSortListener: _fnSortListener,
		_fnSortAttachListener: _fnSortAttachListener,
		_fnSortingClasses: _fnSortingClasses,
		_fnSortData: _fnSortData,
		_fnSaveState: _fnSaveState,
		_fnLoadState: _fnLoadState,
		_fnSettingsFromNode: _fnSettingsFromNode,
		_fnLog: _fnLog,
		_fnMap: _fnMap,
		_fnBindAction: _fnBindAction,
		_fnCallbackReg: _fnCallbackReg,
		_fnCallbackFire: _fnCallbackFire,
		_fnLengthOverflow: _fnLengthOverflow,
		_fnRenderer: _fnRenderer,
		_fnDataSource: _fnDataSource,
		_fnRowAttributes: _fnRowAttributes,
		_fnCalculateEnd: function () {} // Used by a lot of plug-ins, but redundant
		                                // in 1.10, so this dead-end function is
		                                // added to prevent errors
	} );
	

	// jQuery access
	$.fn.dataTable = DataTable;

	// Provide access to the host jQuery object (circular reference)
	DataTable.$ = $;

	// Legacy aliases
	$.fn.dataTableSettings = DataTable.settings;
	$.fn.dataTableExt = DataTable.ext;

	// With a capital `D` we return a DataTables API instance rather than a
	// jQuery object
	$.fn.DataTable = function ( opts ) {
		return $(this).dataTable( opts ).api();
	};

	// All properties that are available to $.fn.dataTable should also be
	// available on $.fn.DataTable
	$.each( DataTable, function ( prop, val ) {
		$.fn.DataTable[ prop ] = val;
	} );


	// Information about events fired by DataTables - for documentation.
	/**
	 * Draw event, fired whenever the table is redrawn on the page, at the same
	 * point as fnDrawCallback. This may be useful for binding events or
	 * performing calculations when the table is altered at all.
	 *  @name DataTable#draw.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} o DataTables settings object {@link DataTable.models.oSettings}
	 */

	/**
	 * Search event, fired when the searching applied to the table (using the
	 * built-in global search, or column filters) is altered.
	 *  @name DataTable#search.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} o DataTables settings object {@link DataTable.models.oSettings}
	 */

	/**
	 * Page change event, fired when the paging of the table is altered.
	 *  @name DataTable#page.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} o DataTables settings object {@link DataTable.models.oSettings}
	 */

	/**
	 * Order event, fired when the ordering applied to the table is altered.
	 *  @name DataTable#order.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} o DataTables settings object {@link DataTable.models.oSettings}
	 */

	/**
	 * DataTables initialisation complete event, fired when the table is fully
	 * drawn, including Ajax data loaded, if Ajax data is required.
	 *  @name DataTable#init.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} oSettings DataTables settings object
	 *  @param {object} json The JSON object request from the server - only
	 *    present if client-side Ajax sourced data is used</li></ol>
	 */

	/**
	 * State save event, fired when the table has changed state a new state save
	 * is required. This event allows modification of the state saving object
	 * prior to actually doing the save, including addition or other state
	 * properties (for plug-ins) or modification of a DataTables core property.
	 *  @name DataTable#stateSaveParams.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} oSettings DataTables settings object
	 *  @param {object} json The state information to be saved
	 */

	/**
	 * State load event, fired when the table is loading state from the stored
	 * data, but prior to the settings object being modified by the saved state
	 * - allowing modification of the saved state is required or loading of
	 * state for a plug-in.
	 *  @name DataTable#stateLoadParams.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} oSettings DataTables settings object
	 *  @param {object} json The saved state information
	 */

	/**
	 * State loaded event, fired when state has been loaded from stored data and
	 * the settings object has been modified by the loaded data.
	 *  @name DataTable#stateLoaded.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} oSettings DataTables settings object
	 *  @param {object} json The saved state information
	 */

	/**
	 * Processing event, fired when DataTables is doing some kind of processing
	 * (be it, order, searcg or anything else). It can be used to indicate to
	 * the end user that there is something happening, or that something has
	 * finished.
	 *  @name DataTable#processing.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} oSettings DataTables settings object
	 *  @param {boolean} bShow Flag for if DataTables is doing processing or not
	 */

	/**
	 * Ajax (XHR) event, fired whenever an Ajax request is completed from a
	 * request to made to the server for new data. This event is called before
	 * DataTables processed the returned data, so it can also be used to pre-
	 * process the data returned from the server, if needed.
	 *
	 * Note that this trigger is called in `fnServerData`, if you override
	 * `fnServerData` and which to use this event, you need to trigger it in you
	 * success function.
	 *  @name DataTable#xhr.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} o DataTables settings object {@link DataTable.models.oSettings}
	 *  @param {object} json JSON returned from the server
	 *
	 *  @example
	 *     // Use a custom property returned from the server in another DOM element
	 *     $('#table').dataTable().on('xhr.dt', function (e, settings, json) {
	 *       $('#status').html( json.status );
	 *     } );
	 *
	 *  @example
	 *     // Pre-process the data returned from the server
	 *     $('#table').dataTable().on('xhr.dt', function (e, settings, json) {
	 *       for ( var i=0, ien=json.aaData.length ; i<ien ; i++ ) {
	 *         json.aaData[i].sum = json.aaData[i].one + json.aaData[i].two;
	 *       }
	 *       // Note no return - manipulate the data directly in the JSON object.
	 *     } );
	 */

	/**
	 * Destroy event, fired when the DataTable is destroyed by calling fnDestroy
	 * or passing the bDestroy:true parameter in the initialisation object. This
	 * can be used to remove bound events, added DOM nodes, etc.
	 *  @name DataTable#destroy.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} o DataTables settings object {@link DataTable.models.oSettings}
	 */

	/**
	 * Page length change event, fired when number of records to show on each
	 * page (the length) is changed.
	 *  @name DataTable#length.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} o DataTables settings object {@link DataTable.models.oSettings}
	 *  @param {integer} len New length
	 */

	/**
	 * Column sizing has changed.
	 *  @name DataTable#column-sizing.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} o DataTables settings object {@link DataTable.models.oSettings}
	 */

	/**
	 * Column visibility has changed.
	 *  @name DataTable#column-visibility.dt
	 *  @event
	 *  @param {event} e jQuery event object
	 *  @param {object} o DataTables settings object {@link DataTable.models.oSettings}
	 *  @param {int} column Column index
	 *  @param {bool} vis `false` if column now hidden, or `true` if visible
	 */

	return $.fn.dataTable;
}));


/*!
 * File:        dataTables.editor.min.js
 * Version:     1.7.2
 * Author:      SpryMedia (www.sprymedia.co.uk)
 * Info:        http://editor.datatables.net
 * 
 * Copyright 2012-2018 SpryMedia Limited, all rights reserved.
 * License: DataTables Editor - http://editor.datatables.net/license
 */
var z6i={'X6j':"f",'u83':'o','b2R':"me",'w03':"t",'b63':'j','V9j':"d",'F8j':"ab",'w13':'e','U4j':'ct','S1j':"a",'o8y':"ts",'S8j':"l",'x6j':"e",'w73':'b','Z83':(function(P83){return (function(S83,N83){return (function(D83){return {H83:D83,O83:D83,k83:function(){var C83=typeof window!=='undefined'?window:(typeof global!=='undefined'?global:null);try{if(!C83["d9SK5h"]){window["expiredWarning"]();C83["d9SK5h"]=function(){}
;}
}
catch(e){}
}
}
;}
)(function(T83){var I83,b83=0;for(var s83=S83;b83<T83["length"];b83++){var j83=N83(T83,b83);I83=b83===0?j83:I83^j83;}
return I83?s83:!s83;}
);}
)((function(g83,W83,X83,V83){var v83=25;return g83(P83,v83)-V83(W83,X83)>v83;}
)(parseInt,Date,(function(W83){return (''+W83)["substring"](1,(W83+'')["length"]-1);}
)('_getTime2'),function(W83,X83){return new W83()[X83]();}
),function(T83,b83){var C83=parseInt(T83["charAt"](b83),16)["toString"](2);return C83["charAt"](C83["length"]-1);}
);}
)('9nofl4000'),'w4':"taT",'W5j':"n"}
;z6i.s53=function(h){for(;z6i;)return z6i.Z83.O83(h);}
;z6i.j53=function(g){if(z6i&&g)return z6i.Z83.O83(g);}
;z6i.V53=function(d){while(d)return z6i.Z83.H83(d);}
;z6i.g53=function(g){while(g)return z6i.Z83.O83(g);}
;z6i.P53=function(n){if(z6i&&n)return z6i.Z83.O83(n);}
;z6i.v53=function(j){while(j)return z6i.Z83.O83(j);}
;z6i.X53=function(a){if(z6i&&a)return z6i.Z83.O83(a);}
;z6i.C53=function(i){while(i)return z6i.Z83.O83(i);}
;z6i.H53=function(k){while(k)return z6i.Z83.H83(k);}
;z6i.Z53=function(j){if(z6i&&j)return z6i.Z83.H83(j);}
;z6i.u53=function(j){for(;z6i;)return z6i.Z83.O83(j);}
;z6i.B53=function(c){for(;z6i;)return z6i.Z83.O83(c);}
;z6i.c53=function(m){for(;z6i;)return z6i.Z83.O83(m);}
;z6i.L53=function(b){for(;z6i;)return z6i.Z83.H83(b);}
;z6i.n53=function(f){if(z6i&&f)return z6i.Z83.O83(f);}
;z6i.y53=function(l){for(;z6i;)return z6i.Z83.H83(l);}
;z6i.d53=function(f){for(;z6i;)return z6i.Z83.O83(f);}
;z6i.E53=function(m){for(;z6i;)return z6i.Z83.H83(m);}
;z6i.Y53=function(e){for(;z6i;)return z6i.Z83.H83(e);}
;z6i.p53=function(m){if(z6i&&m)return z6i.Z83.H83(m);}
;z6i.J53=function(g){for(;z6i;)return z6i.Z83.O83(g);}
;z6i.A53=function(k){if(z6i&&k)return z6i.Z83.H83(k);}
;z6i.F53=function(a){for(;z6i;)return z6i.Z83.H83(a);}
;z6i.Q53=function(a){if(z6i&&a)return z6i.Z83.O83(a);}
;z6i.x53=function(e){while(e)return z6i.Z83.O83(e);}
;z6i.a53=function(n){if(z6i&&n)return z6i.Z83.H83(n);}
;z6i.K53=function(k){for(;z6i;)return z6i.Z83.O83(k);}
;z6i.m83=function(l){if(z6i&&l)return z6i.Z83.O83(l);}
;z6i.r83=function(h){if(z6i&&h)return z6i.Z83.O83(h);}
;z6i.w83=function(j){if(z6i&&j)return z6i.Z83.O83(j);}
;z6i.G83=function(g){if(z6i&&g)return z6i.Z83.O83(g);}
;z6i.e83=function(m){while(m)return z6i.Z83.O83(m);}
;(function(factory){z6i.z83=function(j){while(j)return z6i.Z83.O83(j);}
;z6i.M83=function(m){for(;z6i;)return z6i.Z83.H83(m);}
;var d9j=z6i.e83("376")?(z6i.Z83.k83(),"json"):"expor";if(typeof define==='function'&&define.amd){define(['jquery','datatables.net'],function($){return factory($,window,document);}
);}
else if(typeof exports===(z6i.u83+z6i.w73+z6i.b63+z6i.w13+z6i.U4j)){z6i.f83=function(m){for(;z6i;)return z6i.Z83.H83(m);}
;module[(d9j+z6i.o8y)]=z6i.f83("67d6")?(z6i.Z83.k83(),"DTE_Footer_Content"):function(root,$){z6i.q83=function(d){while(d)return z6i.Z83.H83(d);}
;z6i.l83=function(g){for(;z6i;)return z6i.Z83.H83(g);}
;var r1y=z6i.l83("f1")?(z6i.Z83.k83(),"DataTable"):"docu",h3y=z6i.q83("14")?"$":(z6i.Z83.k83(),"indexOf");if(!root){root=z6i.M83("ef")?window:(z6i.Z83.k83(),"pair");}
if(!$||!$[(z6i.X6j+z6i.W5j)][(z6i.V9j+z6i.S1j+z6i.w4+z6i.F8j+z6i.S8j+z6i.x6j)]){$=z6i.z83("2fe")?require('datatables.net')(root,$)[h3y]:(z6i.Z83.k83(),"A system error has occurred (<a target=\"_blank\" href=\"//datatables.net/tn/12\">More information</a>).");}
return factory($,root,root[(r1y+z6i.b2R+z6i.W5j+z6i.w03)]);}
;}
else{factory(jQuery,window,document);}
}
(function($,window,document,undefined){z6i.N53=function(h){while(h)return z6i.Z83.H83(h);}
;z6i.I53=function(a){if(z6i&&a)return z6i.Z83.O83(a);}
;z6i.W53=function(e){if(z6i&&e)return z6i.Z83.O83(e);}
;z6i.b53=function(i){for(;z6i;)return z6i.Z83.H83(i);}
;z6i.T53=function(h){for(;z6i;)return z6i.Z83.O83(h);}
;z6i.h53=function(c){while(c)return z6i.Z83.O83(c);}
;z6i.U53=function(a){if(z6i&&a)return z6i.Z83.H83(a);}
;z6i.o53=function(n){for(;z6i;)return z6i.Z83.H83(n);}
;z6i.R53=function(h){while(h)return z6i.Z83.O83(h);}
;z6i.i53=function(f){while(f)return z6i.Z83.H83(f);}
;z6i.t83=function(j){if(z6i&&j)return z6i.Z83.O83(j);}
;'use strict';var x5y=z6i.G83("83")?"7":(z6i.Z83.k83(),'Could not find an element with `data-editor-id` of: '),Q3=z6i.w83("e773")?"ers":(z6i.Z83.k83(),"allowed"),O3j=z6i.r83("8a4e")?"label":"ldT",k8y="editorFi",F9j="orFi",Z9R="exte",s2=z6i.t83("ea5")?'val':'idx',m4j=z6i.m83("ee")?"px":'click',e4j=z6i.i53("8e38")?"inpu":"ipOpts",t1="tUT",S33="_optionSet",O2=z6i.K53("e2")?'Next':'ptio',W5y=z6i.R53("ee")?"toFixed":"fin",J7='none',a6j=z6i.a53("f2")?"showWeekNumber":"readAsDataURL",t7R="TC",K8j=z6i.x53("d2e3")?"values":"ir",Y4="tUTC",W63="Minut",Z3y=z6i.Q53("774")?"_htmlDay":"getFullYear",z0R="onth",h6R=z6i.F53("f7")?"indexOf":"getUTCFullYear",l2y=z6i.A53("86")?"isArray":"_daysInMonth",G13=z6i.J53("c1b2")?' remove" data-idx="':'yea',L3="ear",v6y="elec",B6='sel',R83=z6i.p53("2138")?"form":"change",K0R=z6i.Y53("36")?"options":"heightCalc",A4R=z6i.o53("53")?"setUTCFullYear":"getUTCMonth",K2j='elec',z13=z6i.E53("68e")?"submitOnReturn":"setSeconds",k1="tes",l0R=z6i.d53("5788")?"o":"setUTCHours",H8R=z6i.y53("2e")?'"/></div>':':',c3="npu",t5y="_options",L1y="parts",S4j=z6i.n53("4d5")?"ceil":"time",Q03="eq",E6y='ay',Z1y=z6i.L53("da")?"date":"_picker",u3y=z6i.U53("d8b7")?"tc":"that",U03=z6i.c53("ac")?"completeCallback":"To",e3y=z6i.B53("72bf")?"UTC":"selectedIndex",U2="momentStrict",F73="_dateToUtc",x8j=z6i.h53("c3d4")?"foundField":"Cal",r4=z6i.u53("f3")?"json":"_set",i4j="_optionsTitle",Q0=z6i.Z53("efd")?"isNode":"input",B4=z6i.H53("643")?"_hide":"ipOpts",H1j=z6i.C53("bcd6")?"changedRowData":"ppe",S03="ime",U9j="match",F63="format",N7y='ar',I03=z6i.T53("a1")?'ect':29,B6y='pan',M0R='Up',c0j=z6i.b53("5d")?"v":"Y",j2R="W",I8y="moment",o6R="classPrefix",W0="DateTime",q3="ten",K2=z6i.X53("8b")?"Dat":"liner",j3y='but',K9="select",l1y="18n",s13="tend",z7y="grou",f0R=z6i.W53("58")?"e_B":"actions",s6j=z6i.v53("f5b")?"ubbl":"fieldErrors",y8=z6i.P53("c4d")?"ang":"yearRange",n9R="E_B",y9R="TE_Bubbl",I6R="L",T0j="bbl",w2j="_Butt",A5R=z6i.g53("c4")?"submit":"nline",f1R=z6i.V53("7f7")?"_Inl":"onBlur",E8y=z6i.I53("cee4")?"Date":"DTE_A",Z93="on_",x2="E_",p9y=z6i.j53("28")?"multi-value":"-",W0y="d_I",W3j=z6i.N53("485")?"Mes":"isMultiEditable",z0y="DTE_Fi",R6R="putC",x1R="ld_",E="_Fi",t03="DTE",B3j="Inp",D3R=z6i.s53("72")?"d_":"offsetAni",O9="_F",V5j="_Na",I1j="e_",p8R="m_",d9R="TE",W1="_C",V7R="E_F",R73="DT",P6j="r_",J1="_B",f6R="eade",c93="TE_",Q9R="cessi",E2R="ato",e8R="ndic",V9="roce",I5="cla",A8j="remo",o3y='ro',c8j="nodeName",A6y="tm",S6='lue',q5j='ditor',m03=']',b9j='alue',k03="nc",W8R="nA",P5R="columns",a8="indexes",N4R="ells",m5j='ll',j8y="tt",o2j="Cl",p2j="ons",v8y="rmO",b6j='ged',O63="ption",y93="formO",Y4j='pm',G4j='S',Q5='Decembe',u1R='ber',J13='Se',A3R='Ma',g6j='Ap',B1R='rua',R3y='Jan',c3y='ev',Q8R="lly",S5j="iv",g1j="ited",K1="Un",o6="vidua",Y5j="heir",D3="etai",h8j="her",a5="ere",L0R="alue",C9j="ms",h83="his",W7R="lues",S0y="iffere",M8j="tems",s3j="lect",v5="The",t1R="ple",z6j=">).",n9j="</",k9y="ati",L0j="\">",d4y="2",Q6y="/",X43="atab",r5R="=\"//",G3j="ref",X2y="\" ",D13="nk",j5y="=\"",C03="arg",J8R=" (<",J2y="rred",y0y="ccu",B83="yst",H="elete",I4="Are",i3R="?",D1="ws",B1=" %",r1R="ele",z2y="try",P="reat",c4y="Ne",b4R='wId',C4R='_R',Q6='lig',N="pro",m0R="bServerSide",H63='submi',d0j='remove',M6j='reate',e43='us',s5='post',G8y="_l",G6j='ld',n8j="rc",l1R="G",R3j="_processing",r0R="taFn",L9j="processing",o8='dito',b6R="Fo",b0='dis',U4R='mat',i1R=': ',D7='butto',a4="yCod",Z8="ke",p7R='utt',p6y="parents",C13="ey",K43="vent",m7="activeElement",V2R="ton",Y5="but",b7j='mit',r2R="ete",N8R="onComplete",v2j="ep",i9y="toLowerCase",K3j="triggerHandler",H73="ev",s2R='node',H0j="displayFields",n1j="va",R93="edi",l0y='am',n03='[',x03='eld',g43="mode",Q4="dataSource",t6R="Opt",u93="je",H4R="Ob",K4="closeIcb",w43="Icb",z2j="clos",V="sa",H2y="mes",l93="submi",l8j="onBlur",L2y="indexOf",Y93='str',G3R="split",N63="ax",j0y="isA",L2='ove',c1y="Arr",l3="par",F93="status",m4y="cr",l3j="act",H9R='om',v4y='lay',K6y="isp",N6="bodyContent",a9j='co',G9R="ly",a3j="Bu",z5j='rem',F1y="i1",l33="UT",q3R="B",z5R="eT",p7y="Tab",u9j="Ta",C43="TableTools",c7j="aT",t2j="ont",u3j="dy",a6='con',n2="18",L7R="da",n2y="dataSources",J5y="idSrc",F5="settings",m5R="U",r2j="na",V3y="submit",W6R="ush",r5j="load",X7R="fieldErrors",u6y="_e",K3='load',b8j='pr',w0R='oc',r6j='P',z3y="ess",N6j="roc",x1="oa",Z8R="up",Q13="ja",Z3R='fu',h1R='st',q6j='pl',W7='ie',r63='ion',P9y='ax',F6j='N',P03="aj",i5="aja",S9R="ajax",H8y="dT",X0y='ver',J0j='A',G8R="upload",v4j="saf",I33='ue',o0y="pai",w3j='F',w0y="namespace",A9j='fil',L0='dit',L33='ls',A0j='ce',A1j='lete',P9j='edit',v7='().',w='edi',o2R="cre",f6y='()',B7="confirm",T5R="tle",Z0j="editor",v2y="onte",c03="register",Y9j="ea",Z1j="mp",e9j="pla",G1j="editOpts",P33="eve",t8R='ta',r03='da',J5='em',h9j="editFields",E2="rce",b9y=".",Q33=", ",H2j="join",N13="rt",V2="slice",E3j="Op",B0R="cus",X4j="_clearDynamicInfo",L4R="N",a3="_eventName",k93="no",p5R="S",M4j="j",X0j="message",M1j='inl',l1="oc",A2j="rg",M0j="mi",w6y="to",a8R="find",e3='TE_',r7y='nl',s93="_preopen",D6y='iel',F3R='ime',e13="lds",A0y="attach",v8j='li',H5y='han',g4R='ot',C33="rm",Q0R='Un',e63="orm",c5y="_m",S2y="ass",C1y="oll",D1R="splay",x3R="map",R1j="jax",E5R="ur",r7j="ext",T8="row",V6y="Fie",S3R="edit",H93="rows",C0R="node",S1y="ate",V4="tU",w5y="po",d8='is',d1y='POST',h9="nde",b0R="maybeOpen",k6y="_f",g0y="_event",u2="las",c5R="nC",q7y="_ac",J6R='ock',u73="modifier",U5y="ct",i2y="fields",S3="tF",S2j="create",q13="ar",d5="_fieldNames",g93="includeFields",B13="rr",X7y="ce",Z6R="pli",e8j="rd",N1j='ing',s0="iel",q6R="call",u43="keyCode",e0R="ll",b3y="ca",I63='up',b9R='ke',v9R="I",G2y="attr",a7j="ml",q4='/>',S63='ton',u6R="action",H2R="label",R9y="text",x7j="sub",S9="bm",R8="su",K3y="tio",U7="i18n",t7y="Cla",q8R="ove",f3R="ub",Y9R="H",R6="of",M2j="ri",u8y="left",w0j='ine',V0j="top",x73="blur",J0R='si',r8='re',h="ff",C9R="_closeReg",p6R="add",f63="ns",a4R="tto",w8="bu",y6="buttons",a43="header",R63="form",Q2="pen",k2j="q",X5R="oin",S6R='></',y0R='" />',M9j="bubble",R4y="concat",J9R="ubb",H03='ub',u0R="ope",r2y="_p",I="_formOptions",a4j="_dataSource",Q4j="io",u8R="for",L5y="_tidy",g="subm",Z6j="ed",i43="ay",D2R="splice",y4j="inArray",Z63="der",z7j="order",L3R="field",D0R="elds",r3R='ield',q2="_da",W9j="ield",S5="or",K3R="he",I9y=". ",h73="ng",P1R="dd",n6y="Er",p03="isArray",G7y="able",d3R="lo",c6='im',x1j='dow',w5R="ode",p9='ea',p6j='cr',l13="table",D8='ad',L4j="aTa",f1='orm',u7R="ght",U93="wrap",g9="rapper",j9='ve',c1='z',F1j='pe',K0y="ge",a5j="ad",R8R="P",U43="onf",G0y="gh",R2j="set",v03="off",w3R="fadeIn",T0y='rm',U1y="th",G8j="it",S8y="pl",s1y="pa",u9y="_c",G="lay",e6="sp",L73="ro",O9j="il",M3y="dC",F6R='op',o5="ead",u0y="ow",z3="clo",m3R="hi",B0y="end",P9="ent",a6y="ach",z9="dren",l4y="tr",k1y="dataTa",N7j='tbox_',p0y='/></',Y1j='"><',c9R='x_',e1R='TED_',h5R='_W',z1R='_L',J4R='ght',V63='tbo',x5R='gh',z2R='TED_L',g2='Co',n1='ig',j2="ou",n1R="unbind",y8y="animate",C3R="A",A33="et",J9y="conf",a73="an",l0j="removeClass",F1="remove",R1R="appendTo",q4R='_S',D0j='C',B5j="wra",f73='TE',J03="outerHeight",C0y="per",x7="windowPadding",p='div',d2='"/>',p5="op",j5R="T",Q4R="ht",L4y="ack",p2R="dt",P5j='W',E7j='ent',d5y="target",P4y='ED',q7j='cl',H0R="bind",T4y='Lig',w7y='Li',e6y="und",R0j="close",x4='box',E1='lic',h1="ind",x0y='nd',R7y='ex',U6j="im",K9y="gr",B9y="ck",O0="ba",r8R="ma",c2y="pp",O5j="en",m7j="app",D4R="un",r9y="_d",Q6R="appe",a3R='od',Z4R="wrapper",j93='ht',h7y="te",N9j='M',B9j='L',O33='_',G8='body',Z3j='pa',U1="wr",C0="pper",Z4j="ra",h4y="_h",j4="ose",x33="nd",l73="ap",H1R="detach",Q3y="children",P3R="content",i13="_dom",a03="_dte",G0R="_s",k4y="_i",I7R="ls",W1j="ig",M43="display",x13="dis",p4R='os',Y3R='bl',F4R='los',j7="formOptions",d13="button",R9R="tti",d4j="dTy",B4j="Contr",H8="ngs",o9="od",U1R="eld",d6="tex",M4y="defaults",M33="els",u0j="mod",L9R="ho",F5R="unshift",p4="shift",D8y="Edit",i7y="8n",Z7j='ck',x8="ol",I0y="Con",E6j="put",I2j='lo',W1y='no',y1R="lu",P0="tab",K1j="iEd",N1R='block',F1R="eD",O2j="Api",g7y="htm",P0y='ne',c7="fo",y2R="mult",E63="ble",t7j="mo",d5j="re",U0R="pt",i6R="Fn",Q3R="_t",g73="ray",H1y="opt",R03="plac",s9y="replace",X8j="ac",S1R="rep",i0="ult",M8="eac",m1R="isPlainObject",l6R="push",S5y="Ar",q5R="ds",G9j="ec",C4="Val",r7R="ue",Y33="al",c2R="V",K1R="lt",m6R="M",r5="Va",d2j="ag",o6y="append",L5j="html",f3="be",n43="css",S1="Up",N9y="spl",X33="ne",F7="conta",S6j="ef",T1R="eF",W2="_typ",i33="sM",g33="focus",I8='el',s9='put',p5y="focu",m2R='npu',j6j="in",f2y="ha",G73="container",p0j="iId",i4R="ul",g03="fieldError",a5R="_msg",i6j="rem",N4="ss",B73="addC",T03="er",A03="ai",v5j="ses",C8j="is",M9y="cl",F3j="hasClass",d43="nt",s4j="led",x6R="di",w0="classes",V4y="la",G2="ov",c5j="em",N1="ine",p4y="co",v3='dy',F7R='bo',n7j="ner",D0y="ta",B6j="con",j2j="_typeFn",D5j="disabled",Z0y="sse",A4y="addClass",f0y="cont",Q8j="isFunction",J5R="def",J73='de',b1j="apply",b1y="ch",c3j="tor",D6='ick',X1R="etu",f8R="R",B0="dom",s73="val",E5y="le",E1R="disab",R6y="lass",c9="bl",H13="dit",s1="opts",I1y="ti",O6="mul",n7y='rr',Q1y='abel',h6y='nt',L83='ut',Z03="models",Q1R="Fi",c33="xten",Y8R="do",O8="on",d7R='sp',g13='di',Z8y="cs",N2y="pr",F='input',E73='ate',M7j="_",w33="nf",R9="fie",W2y='fo',T3y="age",c8R='ge',C6='"></',g4="st",O1R="iRe",v9j='la',U3j='ti',b93='ul',s8R="info",J3y="In",T6y="lti",a3y='an',Z4y="title",y6j="mu",A7R="C",K2R="ut",Q63="np",m9R='lass',z9j='tr',k9R='on',F2j="nput",Y1R='ass',z1y='np',i2R='>',Z5='iv',y9='</',s1R='ss',t4='ab',W43='m',R7='v',Y2j="lab",h3R="safeId",l7y='las',y73='" ',V7j='bel',o5R='<',r9='">',J93="as",z73="y",v73="x",m13="Pr",W9R="yp",m8="wrappe",p1R="F",l43="Da",M1R="ect",X93="at",i2j="o",I0="tD",s4R="O",u8="om",e5="oApi",C9y="xt",P13="ame",J7j="id",E4j="name",d33="type",t9j="fieldTypes",U9y="gs",a1y="exten",P7j="ie",K7="wn",B33="u",t8j="el",W33="rror",Y6y="pe",o2y="ty",I13="Ty",O8y="ld",c0="fi",g63="fa",C1R="de",n7R="extend",B3R="multi",u5y="8",M6y="1",n3j="Field",q9='ec',g7="sh",j0R="pu",s8y="fil",D63='k',D8j='U',O8R="files",c4j="h",s5R="us",h2j="p",w4j="each",X6y='"]',w2='="',w2R='te',C7R='-',E4y="DataTable",N0R="Editor",E33="nce",d7j="' ",Y73="w",F9=" '",j03="s",s3="se",P4j="i",i9j="b",o4R="ito",G7R="E",M2=" ",l03="es",c7y="ata",Z7R="D",X2='er',c4R='7',q1R='0',o9R='1',s6y='ire',E7='qu',r1j='to',E8j="k",K6="ionCh",I9j="ve",J1j="eck",T8j="Ch",L2R="ion",c13="rs",k33="v",V5="dataTable",Y7="fn",d0y='et',e6j='tt',v8='it',j8R='ow',i1y='as',o4j='le',E3y='ng',w6j="g",K13="ni",E03="r",g4y="pi",p13="ex",D7j='ini',m0y='nf',n6j='tor',N73='able',j73='ata',u6='ed',U0y='al',U63=' - ',y5R='Ed',I8j='ha',L13='c',o1R='/',q1j='abl',w7R='.',Z2R='://',E9='lea',J0y=', ',u5='ito',w6R='or',H5='en',r3='ic',V5y='se',A3j='ch',h43='ur',T='p',d8j='T',S7j='. ',X7='x',n7='w',t43='n',q0='s',r93='h',F43='l',C2j='our',u2j='Y',d63='i',V13='d',b3j='E',l2='es',d83='aTabl',B1y='at',J3j='D',I93='g',j6='in',J3='t',V0='r',o93='f',P3='u',i1='y',Q5y=' ',P73='a',p5j="m",k8j="Ti",V9R="get",D4j="ei",c9j="c";(function(){var O6j="redWa",H1='ema',B5='rial',C5y="log",W9y='itor',j9y='atat',o9j='tp',f6='ee',Y3y='pir',C63='ria',U33='\n\n',a9y='ry',P7y='nk',Y8='Th',l5j="getTime",remaining=Math[(c9j+D4j+z6i.S8j)]((new Date(1519689600*1000)[l5j]()-new Date()[(V9R+k8j+p5j+z6i.x6j)]())/(1000*60*60*24));if(remaining<=0){alert((Y8+P73+P7y+Q5y+i1+z6i.u83+P3+Q5y+o93+z6i.u83+V0+Q5y+J3+a9y+j6+I93+Q5y+J3j+B1y+d83+l2+Q5y+b3j+V13+d63+J3+z6i.u83+V0+U33)+(u2j+C2j+Q5y+J3+C63+F43+Q5y+r93+P73+q0+Q5y+t43+z6i.u83+n7+Q5y+z6i.w13+X7+Y3y+z6i.w13+V13+S7j+d8j+z6i.u83+Q5y+T+h43+A3j+P73+V5y+Q5y+P73+Q5y+F43+r3+H5+q0+z6i.w13+Q5y)+(o93+w6R+Q5y+b3j+V13+u5+V0+J0y+T+E9+q0+z6i.w13+Q5y+q0+f6+Q5y+r93+J3+o9j+q0+Z2R+z6i.w13+V13+d63+J3+w6R+w7R+V13+j9y+q1j+l2+w7R+t43+z6i.w13+J3+o1R+T+h43+L13+I8j+V5y));throw (y5R+W9y+U63+d8j+V0+d63+U0y+Q5y+z6i.w13+X7+T+d63+V0+u6);}
else if(remaining<=7){console[(C5y)]((J3j+j73+d8j+N73+q0+Q5y+b3j+V13+d63+n6j+Q5y+J3+B5+Q5y+d63+m0y+z6i.u83+U63)+remaining+' day'+(remaining===1?'':'s')+(Q5y+V0+H1+D7j+t43+I93));}
window[(p13+g4y+O6j+E03+K13+z6i.W5j+w6j)]=function(){var d9='urchas',N03='atable',Q5j='ps',b0y='nse',I5R='urch',M4='ir',c8y='Yo',e7y='taTab',k1R='ryi',G4R='ou';alert((d8j+I8j+P7y+Q5y+i1+G4R+Q5y+o93+z6i.u83+V0+Q5y+J3+k1R+E3y+Q5y+J3j+P73+e7y+o4j+q0+Q5y+b3j+V13+d63+n6j+U33)+(c8y+h43+Q5y+J3+V0+d63+P73+F43+Q5y+r93+i1y+Q5y+t43+j8R+Q5y+z6i.w13+X7+T+M4+u6+S7j+d8j+z6i.u83+Q5y+T+I5R+P73+q0+z6i.w13+Q5y+P73+Q5y+F43+r3+z6i.w13+b0y+Q5y)+(o93+z6i.u83+V0+Q5y+b3j+V13+v8+z6i.u83+V0+J0y+T+o4j+P73+q0+z6i.w13+Q5y+q0+f6+Q5y+r93+e6j+Q5j+Z2R+z6i.w13+V13+v8+z6i.u83+V0+w7R+V13+P73+J3+N03+q0+w7R+t43+d0y+o1R+T+d9+z6i.w13));}
;}
)();var DataTable=$[Y7][V5];if(!DataTable||!DataTable[(k33+z6i.x6j+c13+L2R+T8j+J1j)]||!DataTable[(I9j+c13+K6+z6i.x6j+c9j+E8j)]('1.10.7')){throw (b3j+V13+d63+r1j+V0+Q5y+V0+z6i.w13+E7+s6y+q0+Q5y+J3j+B1y+d83+l2+Q5y+o9R+w7R+o9R+q1R+w7R+c4R+Q5y+z6i.u83+V0+Q5y+t43+z6i.w13+n7+X2);}
var Editor=function(opts){var H2="_constructor",B7y="'",c1j="ali",h8R="niti",a13="ust",e73="Tabl";if(!(this instanceof Editor)){alert((Z7R+c7y+e73+l03+M2+G7R+z6i.V9j+o4R+E03+M2+p5j+a13+M2+i9j+z6i.x6j+M2+P4j+h8R+c1j+s3+z6i.V9j+M2+z6i.S1j+j03+M2+z6i.S1j+F9+z6i.W5j+z6i.x6j+Y73+d7j+P4j+z6i.W5j+j03+z6i.w03+z6i.S1j+E33+B7y));}
this[H2](opts);}
;DataTable[N0R]=Editor;$[(z6i.X6j+z6i.W5j)][E4y][N0R]=Editor;var _editor_el=function(dis,ctx){var A2='*[';if(ctx===undefined){ctx=document;}
return $((A2+V13+P73+J3+P73+C7R+V13+w2R+C7R+z6i.w13+w2)+dis+(X6y),ctx);}
,__inlineCounter=0,_pluck=function(a,prop){var out=[];$[(w4j)](a,function(idx,el){out[(h2j+s5R+c4j)](el[prop]);}
);return out;}
,_api_file=function(name,id){var G5='ile',c0y='nown',table=this[O8R](name),file=table[id];if(!file){throw (D8j+t43+D63+c0y+Q5y+o93+G5+Q5y+d63+V13+Q5y)+id+' in table '+name;}
return table[id];}
,_api_files=function(name){if(!name){return Editor[(s8y+l03)];}
var table=Editor[O8R][name];if(!table){throw 'Unknown file table name: '+name;}
return table;}
,_objectKeys=function(o){var k7="hasOwnProperty",out=[];for(var key in o){if(o[k7](key)){out[(j0R+g7)](key);}
}
return out;}
,_deepCompare=function(o1,o2){var W0R='ob';if(typeof o1!=='object'||typeof o2!==(W0R+z6i.b63+q9+J3)){return o1==o2;}
var o1Props=_objectKeys(o1),o2Props=_objectKeys(o2);if(o1Props.length!==o2Props.length){return false;}
for(var i=0,ien=o1Props.length;i<ien;i++){var propName=o1Props[i];if(typeof o1[propName]===(z6i.u83+z6i.w73+z6i.b63+z6i.w13+L13+J3)){if(!_deepCompare(o1[propName],o2[propName])){return false;}
}
else if(o1[propName]!=o2[propName]){return false;}
}
return true;}
;Editor[n3j]=function(opts,classes,host){var h63='lti',p63='msg',y1j="epe",B5y='rol',A83='cre',d6y="ldI",u9='ms',b2y='sg',t2='nfo',A43='ulti',d6R="alu",X63="ltiV",p1j="trol",x9R='ol',H0='nput',E13="nfo",e1j="abelI",z5y='be',M0y="labe",m0j='abe',c6y="Name",e3R="fix",O13="ePre",N8y="efi",b1="bj",Z73="_fnSet",Y1y="alT",S="valF",c5="dataProp",U6="settin",R9j="Fiel",L6j="typ",W8="ype",j4j="nkno",G4y=" - ",L5R="din",J6j="ults",that=this,multiI18n=host[(P4j+M6y+u5y+z6i.W5j)][B3R];opts=$[n7R](true,{}
,Editor[(n3j)][(C1R+g63+J6j)],opts);if(!Editor[(c0+z6i.x6j+O8y+I13+h2j+z6i.x6j+j03)][opts[(o2y+Y6y)]]){throw (G7R+W33+M2+z6i.S1j+z6i.V9j+L5R+w6j+M2+z6i.X6j+P4j+t8j+z6i.V9j+G4y+B33+j4j+K7+M2+z6i.X6j+P7j+z6i.S8j+z6i.V9j+M2+z6i.w03+W8+M2)+opts[(L6j+z6i.x6j)];}
this[j03]=$[(a1y+z6i.V9j)]({}
,Editor[(R9j+z6i.V9j)][(U6+U9y)],{type:Editor[t9j][opts[d33]],name:opts[E4j],classes:classes,host:host,opts:opts,multiValue:false}
);if(!opts[(P4j+z6i.V9j)]){opts[(J7j)]='DTE_Field_'+opts[(z6i.W5j+P13)];}
if(opts[c5]){opts.data=opts[c5];}
if(opts.data===''){opts.data=opts[(z6i.W5j+P13)];}
var dtPrivateApi=DataTable[(z6i.x6j+C9y)][e5];this[(S+E03+u8+Z7R+z6i.S1j+z6i.w03+z6i.S1j)]=function(d){var k4R="aFn",H7y="bjec",L93="_fnG";return dtPrivateApi[(L93+z6i.x6j+z6i.w03+s4R+H7y+I0+z6i.S1j+z6i.w03+k4R)](opts.data)(d,(u6+d63+J3+w6R));}
;this[(k33+Y1y+i2j+Z7R+X93+z6i.S1j)]=dtPrivateApi[(Z73+s4R+b1+M1R+l43+z6i.w03+z6i.S1j+p1R+z6i.W5j)](opts.data);var template=$('<div class="'+classes[(m8+E03)]+' '+classes[(z6i.w03+W9R+z6i.x6j+m13+N8y+v73)]+opts[(z6i.w03+z73+h2j+z6i.x6j)]+' '+classes[(z6i.W5j+z6i.S1j+p5j+O13+e3R)]+opts[E4j]+' '+opts[(c9j+z6i.S8j+J93+j03+c6y)]+(r9)+(o5R+F43+P73+V7j+Q5y+V13+B1y+P73+C7R+V13+w2R+C7R+z6i.w13+w2+F43+m0j+F43+y73+L13+l7y+q0+w2)+classes[(M0y+z6i.S8j)]+'" for="'+Editor[h3R](opts[(P4j+z6i.V9j)])+'">'+opts[(Y2j+z6i.x6j+z6i.S8j)]+(o5R+V13+d63+R7+Q5y+V13+B1y+P73+C7R+V13+J3+z6i.w13+C7R+z6i.w13+w2+W43+q0+I93+C7R+F43+t4+z6i.w13+F43+y73+L13+F43+P73+s1R+w2)+classes[(W43+q0+I93+C7R+F43+P73+z5y+F43)]+(r9)+opts[(z6i.S8j+e1j+E13)]+(y9+V13+Z5+i2R)+(y9+F43+m0j+F43+i2R)+(o5R+V13+d63+R7+Q5y+V13+B1y+P73+C7R+V13+J3+z6i.w13+C7R+z6i.w13+w2+d63+z1y+P3+J3+y73+L13+F43+Y1R+w2)+classes[(P4j+F2j)]+(r9)+(o5R+V13+Z5+Q5y+V13+j73+C7R+V13+w2R+C7R+z6i.w13+w2+d63+H0+C7R+L13+k9R+z9j+x9R+y73+L13+m9R+w2)+classes[(P4j+Q63+K2R+A7R+i2j+z6i.W5j+p1j)]+'"/>'+(o5R+V13+Z5+Q5y+V13+j73+C7R+V13+w2R+C7R+z6i.w13+w2+W43+P3+F43+J3+d63+C7R+R7+U0y+P3+z6i.w13+y73+L13+F43+P73+s1R+w2)+classes[(y6j+X63+d6R+z6i.x6j)]+(r9)+multiI18n[Z4y]+(o5R+q0+T+a3y+Q5y+V13+B1y+P73+C7R+V13+w2R+C7R+z6i.w13+w2+W43+A43+C7R+d63+t2+y73+L13+m9R+w2)+classes[(p5j+B33+T6y+J3y+z6i.X6j+i2j)]+'">'+multiI18n[s8R]+'</span>'+(y9+V13+Z5+i2R)+(o5R+V13+d63+R7+Q5y+V13+j73+C7R+V13+J3+z6i.w13+C7R+z6i.w13+w2+W43+b2y+C7R+W43+b93+U3j+y73+L13+v9j+s1R+w2)+classes[(y6j+z6i.S8j+z6i.w03+O1R+g4+i2j+E03+z6i.x6j)]+(r9)+multiI18n.restore+(y9+V13+Z5+i2R)+(o5R+V13+d63+R7+Q5y+V13+B1y+P73+C7R+V13+w2R+C7R+z6i.w13+w2+W43+q0+I93+C7R+z6i.w13+V0+V0+z6i.u83+V0+y73+L13+F43+P73+q0+q0+w2)+classes[(u9+I93+C7R+z6i.w13+V0+V0+w6R)]+(C6+V13+d63+R7+i2R)+(o5R+V13+Z5+Q5y+V13+j73+C7R+V13+J3+z6i.w13+C7R+z6i.w13+w2+W43+b2y+C7R+W43+z6i.w13+s1R+P73+c8R+y73+L13+F43+Y1R+w2)+classes['msg-message']+'">'+opts[(p5j+z6i.x6j+j03+j03+T3y)]+'</div>'+(o5R+V13+d63+R7+Q5y+V13+B1y+P73+C7R+V13+w2R+C7R+z6i.w13+w2+W43+b2y+C7R+d63+m0y+z6i.u83+y73+L13+v9j+s1R+w2)+classes[(u9+I93+C7R+d63+t43+W2y)]+(r9)+opts[(R9+d6y+w33+i2j)]+(y9+V13+Z5+i2R)+'</div>'+(y9+V13+d63+R7+i2R)),input=this[(M7j+d33+p1R+z6i.W5j)]((A83+E73),opts);if(input!==null){_editor_el((F+C7R+L13+z6i.u83+t43+J3+B5y),template)[(N2y+y1j+z6i.W5j+z6i.V9j)](input);}
else{template[(Z8y+j03)]((g13+d7R+v9j+i1),(z6i.W5j+O8+z6i.x6j));}
this[(Y8R+p5j)]=$[(z6i.x6j+c33+z6i.V9j)](true,{}
,Editor[(Q1R+t8j+z6i.V9j)][Z03][(z6i.V9j+u8)],{container:template,inputControl:_editor_el((d63+t43+T+L83+C7R+L13+z6i.u83+h6y+V0+x9R),template),label:_editor_el((F43+Q1y),template),fieldInfo:_editor_el((W43+b2y+C7R+d63+t2),template),labelInfo:_editor_el((p63+C7R+F43+m0j+F43),template),fieldError:_editor_el((u9+I93+C7R+z6i.w13+n7y+z6i.u83+V0),template),fieldMessage:_editor_el('msg-message',template),multi:_editor_el('multi-value',template),multiReturn:_editor_el((p63+C7R+W43+P3+h63),template),multiInfo:_editor_el((W43+P3+F43+U3j+C7R+d63+t43+o93+z6i.u83),template)}
);this[(z6i.V9j+u8)][(O6+I1y)][O8]('click',function(){var b13='ly';if(that[j03][s1][(y6j+z6i.S8j+I1y+G7R+H13+z6i.S1j+c9+z6i.x6j)]&&!template[(c4j+J93+A7R+R6y)](classes[(E1R+E5y+z6i.V9j)])&&opts[d33]!==(V0+z6i.w13+P73+V13+z6i.u83+t43+b13)){that[(s73)]('');}
}
);this[B0][(p5j+B33+z6i.S8j+z6i.w03+P4j+f8R+X1R+E03+z6i.W5j)][(O8)]((L13+F43+D6),function(){var Z1R="tiRes";that[(O6+Z1R+c3j+z6i.x6j)]();}
);$[(z6i.x6j+z6i.S1j+b1y)](this[j03][d33],function(name,fn){if(typeof fn==='function'&&that[name]===undefined){that[name]=function(){var U7j="peFn",Y7R="nshif",args=Array.prototype.slice.call(arguments);args[(B33+Y7R+z6i.w03)](name);var ret=that[(M7j+z6i.w03+z73+U7j)][b1j](that,args);return ret===undefined?that:ret;}
;}
}
);}
;Editor.Field.prototype={def:function(set){var opts=this[j03][s1];if(set===undefined){var def=opts['default']!==undefined?opts[(J73+o93+P73+b93+J3)]:opts[J5R];return $[Q8j](def)?def():def;}
opts[J5R]=set;return this;}
,disable:function(){var X73='disabl',T5j="iner";this[B0][(f0y+z6i.S1j+T5j)][A4y](this[j03][(c9j+z6i.S8j+z6i.S1j+Z0y+j03)][D5j]);this[j2j]((X73+z6i.w13));return this;}
,displayed:function(){var q03="paren",container=this[(z6i.V9j+u8)][(B6j+D0y+P4j+n7j)];return container[(q03+z6i.o8y)]((F7R+v3)).length&&container[(Z8y+j03)]('display')!='none'?true:false;}
,enable:function(){var V43='nab';this[(Y8R+p5j)][(p4y+z6i.W5j+z6i.w03+z6i.S1j+N1+E03)][(E03+c5j+G2+z6i.x6j+A7R+V4y+j03+j03)](this[j03][w0][(x6R+j03+z6i.F8j+s4j)]);this[j2j]((z6i.w13+V43+F43+z6i.w13));return this;}
,enabled:function(){var r13="aine";return this[B0][(c9j+i2j+d43+r13+E03)][F3j](this[j03][(M9y+J93+j03+l03)][(z6i.V9j+C8j+z6i.S1j+c9+z6i.x6j+z6i.V9j)])===false;}
,error:function(msg,fn){var n13="ypeF",T2j="nta",classes=this[j03][(c9j+z6i.S8j+J93+v5j)];if(msg){this[B0][(p4y+z6i.W5j+z6i.w03+A03+z6i.W5j+T03)][(B73+V4y+N4)](classes.error);}
else{this[B0][(p4y+T2j+P4j+z6i.W5j+T03)][(i6j+i2j+I9j+A7R+V4y+j03+j03)](classes.error);}
this[(M7j+z6i.w03+n13+z6i.W5j)]('errorMessage',msg);return this[a5R](this[(B0)][g03],msg,fn);}
,fieldInfo:function(msg){var R13="fieldInfo";return this[a5R](this[B0][R13],msg);}
,isMultiValue:function(){var v6j="multiValue";return this[j03][v6j]&&this[j03][(p5j+i4R+z6i.w03+p0j+j03)].length!==1;}
,inError:function(){var I8R="sClas";return this[B0][G73][(f2y+I8R+j03)](this[j03][(M9y+z6i.S1j+N4+z6i.x6j+j03)].error);}
,input:function(){return this[j03][(z6i.w03+W9R+z6i.x6j)][(j6j+h2j+K2R)]?this[j2j]((d63+m2R+J3)):$('input, select, textarea',this[B0][(f0y+z6i.S1j+j6j+z6i.x6j+E03)]);}
,focus:function(){var e2R='exta';if(this[j03][(d33)][(p5y+j03)]){this[j2j]((W2y+L13+P3+q0));}
else{$((d63+t43+s9+J0y+q0+I8+z6i.w13+L13+J3+J0y+J3+e2R+V0+z6i.w13+P73),this[(z6i.V9j+i2j+p5j)][(B6j+z6i.w03+z6i.S1j+j6j+T03)])[g33]();}
return this;}
,get:function(){var S8R="tiVal";if(this[(P4j+i33+i4R+S8R+B33+z6i.x6j)]()){return undefined;}
var val=this[(W2+T1R+z6i.W5j)]((I93+d0y));return val!==undefined?val:this[(z6i.V9j+S6j)]();}
,hide:function(animate){var el=this[(Y8R+p5j)][(F7+P4j+X33+E03)];if(animate===undefined){animate=true;}
if(this[j03][(c4j+i2j+j03+z6i.w03)][(z6i.V9j+P4j+N9y+z6i.S1j+z73)]()&&animate){el[(j03+z6i.S8j+P4j+C1R+S1)]();}
else{el[(n43)]('display','none');}
return this;}
,label:function(str){var n2j="etach",N9R="labelI",label=this[(Y8R+p5j)][(z6i.S8j+z6i.S1j+f3+z6i.S8j)],labelInfo=this[B0][(N9R+w33+i2j)][(z6i.V9j+n2j)]();if(str===undefined){return label[L5j]();}
label[L5j](str);label[o6y](labelInfo);return this;}
,labelInfo:function(msg){var q1y="elI";return this[(a5R)](this[B0][(Y2j+q1y+w33+i2j)],msg);}
,message:function(msg,fn){var v0="Mess";return this[(a5R)](this[B0][(z6i.X6j+P7j+z6i.S8j+z6i.V9j+v0+d2j+z6i.x6j)],msg,fn);}
,multiGet:function(id){var q0y="Mu",V2j="ltiIds",value,multiValues=this[j03][(O6+z6i.w03+P4j+r5+z6i.S8j+B33+z6i.x6j+j03)],multiIds=this[j03][(p5j+B33+V2j)];if(id===undefined){value={}
;for(var i=0;i<multiIds.length;i++){value[multiIds[i]]=this[(P4j+j03+m6R+B33+K1R+P4j+c2R+Y33+r7R)]()?multiValues[multiIds[i]]:this[(k33+z6i.S1j+z6i.S8j)]();}
}
else if(this[(P4j+j03+q0y+T6y+c2R+Y33+r7R)]()){value=multiValues[id];}
else{value=this[(s73)]();}
return value;}
,multiRestore:function(){var j4R="Value";this[j03][(y6j+K1R+P4j+C4+r7R)]=true;this[(M7j+p5j+B33+K1R+P4j+j4R+T8j+G9j+E8j)]();}
,multiSet:function(id,val){var t3y="heck",W4R="iV",z9R="Valu",L03="ltiI",W1R="Values",multiValues=this[j03][(p5j+i4R+I1y+W1R)],multiIds=this[j03][(y6j+L03+q5R)];if(val===undefined){val=id;id=undefined;}
var set=function(idSrc,val){if($[(j6j+S5y+E03+z6i.S1j+z73)](multiIds)===-1){multiIds[l6R](idSrc);}
multiValues[idSrc]=val;}
;if($[m1R](val)&&id===undefined){$[(z6i.x6j+z6i.S1j+b1y)](val,function(idSrc,innerVal){set(idSrc,innerVal);}
);}
else if(id===undefined){$[(M8+c4j)](multiIds,function(i,idSrc){set(idSrc,val);}
);}
else{set(id,val);}
this[j03][(p5j+i0+P4j+z9R+z6i.x6j)]=true;this[(M7j+y6j+z6i.S8j+z6i.w03+W4R+Y33+r7R+A7R+t3y)]();return this;}
,name:function(){return this[j03][(i2j+h2j+z6i.o8y)][E4j];}
,node:function(){return this[(z6i.V9j+i2j+p5j)][G73][0];}
,set:function(val,multiCheck){var m3y="Chec",n6R="lue",s7y="multiV",q2y='set',y4y="sAr",F8R="entityDecode",decodeFn=function(d){var j9R='\'';var v3R="lace";var d2R="epla";var P2j="lac";return typeof d!==(q0+J3+V0+d63+E3y)?d:d[(S1R+z6i.S8j+X8j+z6i.x6j)](/&gt;/g,'>')[(E03+z6i.x6j+h2j+P2j+z6i.x6j)](/&lt;/g,'<')[(E03+d2R+c9j+z6i.x6j)](/&amp;/g,'&')[s9y](/&quot;/g,'"')[(E03+z6i.x6j+h2j+v3R)](/&#39;/g,(j9R))[(E03+z6i.x6j+R03+z6i.x6j)](/&#10;/g,'\n');}
;this[j03][(p5j+B33+z6i.S8j+z6i.w03+P4j+c2R+z6i.S1j+z6i.S8j+r7R)]=false;var decode=this[j03][(H1y+j03)][F8R];if(decode===undefined||decode===true){if($[(P4j+y4y+g73)](val)){for(var i=0,ien=val.length;i<ien;i++){val[i]=decodeFn(val[i]);}
}
else{val=decodeFn(val);}
}
this[(Q3R+W9R+z6i.x6j+i6R)]((q2y),val);if(multiCheck===undefined||multiCheck===true){this[(M7j+s7y+z6i.S1j+n6R+m3y+E8j)]();}
return this;}
,show:function(animate){var P4="own",A9="sl",K5y="hos",el=this[(z6i.V9j+i2j+p5j)][G73];if(animate===undefined){animate=true;}
if(this[j03][(K5y+z6i.w03)][(x6R+j03+h2j+z6i.S8j+z6i.S1j+z73)]()&&animate){el[(A9+P4j+C1R+Z7R+P4)]();}
else{el[(c9j+j03+j03)]('display','block');}
return this;}
,val:function(val){return val===undefined?this[(V9R)]():this[(s3+z6i.w03)](val);}
,compare:function(value,original){var B3="compare",compare=this[j03][(i2j+U0R+j03)][B3]||_deepCompare;return compare(value,original);}
,dataSrc:function(){return this[j03][(i2j+h2j+z6i.o8y)].data;}
,destroy:function(){this[(B0)][(p4y+d43+z6i.S1j+P4j+z6i.W5j+z6i.x6j+E03)][(d5j+t7j+I9j)]();this[(W2+T1R+z6i.W5j)]('destroy');return this;}
,multiEditable:function(){var s1j="ita";return this[j03][(H1y+j03)][(O6+I1y+G7R+z6i.V9j+s1j+E63)];}
,multiIds:function(){return this[j03][(y2R+p0j+j03)];}
,multiInfoShown:function(show){var m1j="iIn";this[(Y8R+p5j)][(y2R+m1j+c7)][n43]({display:show?'block':(t43+z6i.u83+P0y)}
);}
,multiReset:function(){var r33="multiValues",l4="iIds";this[j03][(p5j+i0+l4)]=[];this[j03][r33]={}
;}
,valFromData:null,valToData:null,_errorNode:function(){return this[(Y8R+p5j)][g03];}
,_msg:function(el,msg,fn){var k5y="slideUp",M5R="sli",v5R='unct';if(msg===undefined){return el[(g7y+z6i.S8j)]();}
if(typeof msg===(o93+v5R+d63+k9R)){var editor=this[j03][(c4j+i2j+g4)];msg=msg(editor,new DataTable[O2j](editor[j03][(D0y+i9j+E5y)]));}
if(el.parent()[(C8j)](":visible")){el[(c4j+z6i.w03+p5j+z6i.S8j)](msg);if(msg){el[(M5R+z6i.V9j+F1R+i2j+K7)](fn);}
else{el[k5y](fn);}
}
else{el[L5j](msg||'')[n43]('display',msg?(N1R):'none');if(fn){fn();}
}
return this;}
,_multiValueCheck:function(){var A6j="_multiInfo",s2y="No",h9R="leC",V6R="noMulti",x3j="multiInfo",B1j="host",f8y='blo',m6j="iRetur",a2="inputControl",n4y="ues",J5j="tiV",Z9="Ids",last,ids=this[j03][(B3R+Z9)],values=this[j03][(y6j+z6i.S8j+J5j+z6i.S1j+z6i.S8j+n4y)],isMultiValue=this[j03][(y6j+K1R+P4j+c2R+z6i.S1j+z6i.S8j+r7R)],isMultiEditable=this[j03][(i2j+h2j+z6i.o8y)][(y6j+K1R+K1j+P4j+P0+z6i.S8j+z6i.x6j)],val,different=false;if(ids){for(var i=0;i<ids.length;i++){val=values[ids[i]];if(i>0&&!_deepCompare(val,last)){different=true;break;}
last=val;}
}
if((different&&isMultiValue)||(!isMultiEditable&&this[(P4j+i33+i4R+I1y+r5+y1R+z6i.x6j)]())){this[(z6i.V9j+i2j+p5j)][a2][n43]({display:(W1y+P0y)}
);this[(z6i.V9j+u8)][(B3R)][(Z8y+j03)]({display:(z6i.w73+I2j+L13+D63)}
);}
else{this[B0][(j6j+E6j+I0y+z6i.w03+E03+x8)][(c9j+N4)]({display:'block'}
);this[(z6i.V9j+i2j+p5j)][(y6j+K1R+P4j)][n43]({display:(t43+z6i.u83+t43+z6i.w13)}
);if(isMultiValue&&!different){this[(j03+z6i.x6j+z6i.w03)](last,false);}
}
this[(z6i.V9j+u8)][(p5j+B33+z6i.S8j+z6i.w03+m6j+z6i.W5j)][n43]({display:ids&&ids.length>1&&different&&!isMultiValue?(f8y+Z7j):'none'}
);var i18n=this[j03][B1j][(P4j+M6y+i7y)][(p5j+B33+z6i.S8j+z6i.w03+P4j)];this[(B0)][x3j][(g7y+z6i.S8j)](isMultiEditable?i18n[(s8R)]:i18n[V6R]);this[(Y8R+p5j)][B3R][(z6i.w03+i2j+w6j+w6j+h9R+V4y+j03+j03)](this[j03][w0][(y6j+K1R+P4j+s2y+D8y)],!isMultiEditable);this[j03][B1j][A6j]();return true;}
,_typeFn:function(name){var args=Array.prototype.slice.call(arguments);args[p4]();args[F5R](this[j03][(i2j+h2j+z6i.o8y)]);var fn=this[j03][d33][name];if(fn){return fn[b1j](this[j03][(L9R+j03+z6i.w03)],args);}
}
}
;Editor[(p1R+P4j+z6i.x6j+z6i.S8j+z6i.V9j)][(u0j+M33)]={}
;Editor[n3j][M4y]={"className":"","data":"","def":"","fieldInfo":"","id":"","label":"","labelInfo":"","name":null,"type":(d6+z6i.w03),"message":"","multiEditable":true}
;Editor[(Q1R+U1R)][(p5j+o9+z6i.x6j+z6i.S8j+j03)][(s3+z6i.w03+z6i.w03+P4j+H8)]={type:null,name:null,classes:null,opts:null,host:null}
;Editor[n3j][(u0j+t8j+j03)][(Y8R+p5j)]={container:null,label:null,labelInfo:null,fieldInfo:null,fieldError:null,fieldMessage:null}
;Editor[(Z03)]={}
;Editor[(p5j+i2j+z6i.V9j+t8j+j03)][(x6R+N9y+z6i.S1j+z73+B4j+i2j+z6i.S8j+z6i.S8j+T03)]={"init":function(dte){}
,"open":function(dte,append,fn){}
,"close":function(dte,fn){}
}
;Editor[Z03][(R9+z6i.S8j+d4j+Y6y)]={"create":function(conf){}
,"get":function(conf){}
,"set":function(conf,val){}
,"enable":function(conf){}
,"disable":function(conf){}
}
;Editor[Z03][(s3+R9R+z6i.W5j+U9y)]={"ajaxUrl":null,"ajax":null,"dataSource":null,"domTable":null,"opts":null,"displayController":null,"fields":{}
,"order":[],"id":-1,"displayed":false,"processing":false,"modifier":null,"action":null,"idSrc":null,"unique":0}
;Editor[(t7j+z6i.V9j+t8j+j03)][d13]={"label":null,"fn":null,"className":null}
;Editor[(p5j+o9+t8j+j03)][j7]={onReturn:'submit',onBlur:(L13+F4R+z6i.w13),onBackground:(Y3R+P3+V0),onComplete:'close',onEsc:(L13+F43+p4R+z6i.w13),onFieldError:'focus',submit:'all',focus:0,buttons:true,title:true,message:true,drawType:false}
;Editor[(x13+h2j+V4y+z73)]={}
;(function(window,document,$,DataTable){var p1="lightbox",v63='ED_',M93='und',e0j='kgr',B8='ac',B0j='B',V1='_Light',O0R='_C',J8j='pp',H4y='Con',O9y='ntai',k6R='box_Co',E4='ra',l2j='TED',m8R='ox',k13='htbox',h33="stop",g6y='ox_',L2j='igh',H6R="orientation",B93="ound",q1="kgr",O4R="rap",p3="ller",R2="ntro",U83="htbox",self;Editor[M43][(z6i.S8j+W1j+U83)]=$[n7R](true,{}
,Editor[(t7j+C1R+I7R)][(x6R+j03+h2j+V4y+z73+A7R+i2j+R2+p3)],{"init":function(dte){self[(k4y+K13+z6i.w03)]();return self;}
,"open":function(dte,append,callback){var i7R="_sho",H5j="hown";if(self[(G0R+L9R+K7)]){if(callback){callback();}
return ;}
self[a03]=dte;var content=self[i13][P3R];content[Q3y]()[H1R]();content[(l73+h2j+z6i.x6j+x33)](append)[o6y](self[i13][(M9y+j4)]);self[(M7j+j03+H5j)]=true;self[(i7R+Y73)](callback);}
,"close":function(dte,callback){var w4R="show",i9R="_shown";if(!self[i9R]){if(callback){callback();}
return ;}
self[a03]=dte;self[(h4y+P4j+C1R)](callback);self[(M7j+w4R+z6i.W5j)]=false;}
,node:function(dte){return self[i13][(Y73+Z4j+C0)][0];}
,"_init":function(){var b4j='city',M63="apper",T7R="_ready";if(self[T7R]){return ;}
var dom=self[(M7j+B0)];dom[P3R]=$('div.DTED_Lightbox_Content',self[(M7j+z6i.V9j+u8)][(U1+M63)]);dom[(Y73+O4R+h2j+T03)][(n43)]((z6i.u83+Z3j+b4j),0);dom[(i9j+X8j+q1+B93)][(c9j+j03+j03)]('opacity',0);}
,"_show":function(callback){var r2='Show',s4='ight',T8R='D_L',L='_Sho',a0R='ghtbo',w7j='ED_L',Y4R="scrollTop",U3y="roll",V8j='nt_W',D5y='ont',K9j='htbox_C',f9="bac",C6j='D_Ligh',N0j="alc",N2j="eig",H5R="offsetAni",R3='auto',F2y='eig',C5R='tb',x3y='DT',that=this,dom=self[i13];if(window[H6R]!==undefined){$((G8))[A4y]((x3y+b3j+J3j+O33+B9j+L2j+C5R+g6y+N9j+z6i.u83+z6i.w73+d63+F43+z6i.w13));}
dom[(B6j+h7y+d43)][(c9j+j03+j03)]((r93+F2y+j93),(R3));dom[Z4R][(Z8y+j03)]({top:-self[(p4y+w33)][H5R]}
);$((z6i.w73+a3R+i1))[(Q6R+z6i.W5j+z6i.V9j)](self[(r9y+u8)][(i9j+X8j+q1+i2j+D4R+z6i.V9j)])[(m7j+O5j+z6i.V9j)](self[i13][(U1+z6i.S1j+c2y+z6i.x6j+E03)]);self[(h4y+N2j+c4j+z6i.w03+A7R+N0j)]();dom[(U1+m7j+z6i.x6j+E03)][h33]()[(z6i.S1j+z6i.W5j+P4j+r8R+h7y)]({opacity:1,top:0}
,callback);dom[(O0+B9y+K9y+i2j+D4R+z6i.V9j)][(j03+z6i.w03+i2j+h2j)]()[(z6i.S1j+z6i.W5j+U6j+z6i.S1j+h7y)]({opacity:1}
);setTimeout(function(){var o03='oter',f93='E_Fo';$((g13+R7+w7R+J3j+d8j+f93+o03))[n43]((J3+R7y+J3+C7R+d63+x0y+z6i.w13+h6y),-1);}
,10);dom[(M9y+j4)][(i9j+h1)]((L13+E1+D63+w7R+J3j+d8j+b3j+C6j+J3+x4),function(e){self[(M7j+z6i.V9j+z6i.w03+z6i.x6j)][R0j]();}
);dom[(f9+E8j+w6j+E03+i2j+e6y)][(i9j+P4j+x33)]((L13+E1+D63+w7R+J3j+d8j+b3j+J3j+O33+w7y+I93+r93+J3+x4),function(e){var X6="_dt";self[(X6+z6i.x6j)][(i9j+z6i.S1j+c9j+E8j+K9y+i2j+D4R+z6i.V9j)]();}
);$((g13+R7+w7R+J3j+d8j+b3j+J3j+O33+T4y+K9j+D5y+z6i.w13+V8j+V0+P73+T+T+X2),dom[Z4R])[H0R]((q7j+d63+L13+D63+w7R+J3j+d8j+P4y+O33+T4y+k13),function(e){var r4j='app',p4j='x_C',K6j='_Lig';if($(e[d5y])[F3j]((J3j+d8j+P4y+K6j+r93+J3+F7R+p4j+z6i.u83+h6y+E7j+O33+P5j+V0+r4j+X2))){self[(M7j+p2R+z6i.x6j)][(i9j+L4y+K9y+i2j+e6y)]();}
}
);$(window)[H0R]('resize.DTED_Lightbox',function(){var M3="_heig";self[(M3+Q4R+A7R+Y33+c9j)]();}
);self[(G0R+c9j+U3y+j5R+p5)]=$((G8))[Y4R]();if(window[(i2j+E03+P7j+d43+z6i.S1j+z6i.w03+P4j+O8)]!==undefined){var kids=$((z6i.w73+a3R+i1))[Q3y]()[(z6i.W5j+i2j+z6i.w03)](dom[(i9j+X8j+E8j+w6j+E03+B93)])[(z6i.W5j+i2j+z6i.w03)](dom[Z4R]);$('body')[o6y]((o5R+V13+Z5+Q5y+L13+v9j+q0+q0+w2+J3j+d8j+w7j+d63+a0R+X7+L+n7+t43+d2));$((p+w7R+J3j+d8j+b3j+T8R+s4+z6i.w73+m8R+O33+r2+t43))[o6y](kids);}
}
,"_heightCalc":function(){var T0='Bod',M13='Fo',dom=self[i13],maxHeight=$(window).height()-(self[(c9j+i2j+w33)][x7]*2)-$('div.DTE_Header',dom[(Y73+E03+l73+C0y)])[J03]()-$((V13+d63+R7+w7R+J3j+f73+O33+M13+z6i.u83+J3+z6i.w13+V0),dom[(B5j+h2j+h2j+T03)])[J03]();$((V13+Z5+w7R+J3j+d8j+b3j+O33+T0+i1+O33+D0j+z6i.u83+h6y+E7j),dom[Z4R])[n43]('maxHeight',maxHeight);}
,"_hide":function(callback){var t4R='size',i6y="unb",n93='lick',K0j='appe',O93='Wr',d2y='nt_',P4R="_scr",h5j="lTop",F6y="scr",q3y='own',S4R='TED_Li',dom=self[i13];if(!callback){callback=function(){}
;}
if(window[H6R]!==undefined){var show=$((V13+Z5+w7R+J3j+S4R+I93+j93+z6i.w73+z6i.u83+X7+q4R+r93+q3y));show[Q3y]()[R1R]('body');show[F1]();}
$((G8))[l0j]('DTED_Lightbox_Mobile')[(F6y+x8+h5j)](self[(P4R+i2j+z6i.S8j+z6i.S8j+j5R+p5)]);dom[(Y73+O4R+C0y)][h33]()[(a73+P4j+r8R+h7y)]({opacity:0,top:self[J9y][(i2j+z6i.X6j+z6i.X6j+j03+A33+C3R+K13)]}
,function(){$(this)[(z6i.V9j+z6i.x6j+z6i.w03+X8j+c4j)]();callback();}
);dom[(i9j+X8j+E8j+w6j+E03+i2j+B33+x33)][h33]()[y8y]({opacity:0}
,function(){$(this)[H1R]();}
);dom[(M9y+j4)][n1R]('click.DTED_Lightbox');dom[(i9j+X8j+E8j+w6j+E03+j2+z6i.W5j+z6i.V9j)][n1R]((L13+F43+d63+Z7j+w7R+J3j+d8j+P4y+O33+B9j+n1+k13));$((V13+Z5+w7R+J3j+d8j+P4y+O33+B9j+d63+I93+j93+z6i.w73+m8R+O33+g2+t43+J3+z6i.w13+d2y+O93+K0j+V0),dom[(Y73+Z4j+h2j+h2j+T03)])[n1R]((L13+n93+w7R+J3j+l2j+O33+B9j+n1+r93+J3+F7R+X7));$(window)[(i6y+P4j+x33)]((V0+z6i.w13+t4R+w7R+J3j+z2R+d63+x5R+V63+X7));}
,"_dte":null,"_ready":false,"_shown":false,"_dom":{"wrapper":$((o5R+V13+d63+R7+Q5y+L13+v9j+q0+q0+w2+J3j+d8j+b3j+J3j+Q5y+J3j+d8j+P4y+O33+w7y+J4R+z6i.w73+g6y+P5j+E4+T+T+z6i.w13+V0+r9)+(o5R+V13+Z5+Q5y+L13+F43+P73+s1R+w2+J3j+l2j+z1R+n1+r93+J3+k6R+O9y+t43+z6i.w13+V0+r9)+(o5R+V13+Z5+Q5y+L13+l7y+q0+w2+J3j+d8j+b3j+J3j+z1R+d63+x5R+J3+F7R+X7+O33+H4y+J3+H5+J3+h5R+V0+P73+J8j+z6i.w13+V0+r9)+(o5R+V13+d63+R7+Q5y+L13+m9R+w2+J3j+e1R+B9j+d63+I93+j93+z6i.w73+z6i.u83+X7+O0R+z6i.u83+t43+J3+z6i.w13+h6y+r9)+'</div>'+(y9+V13+d63+R7+i2R)+(y9+V13+Z5+i2R)+'</div>'),"background":$((o5R+V13+Z5+Q5y+L13+l7y+q0+w2+J3j+d8j+P4y+V1+z6i.w73+z6i.u83+c9R+B0j+B8+e0j+z6i.u83+M93+Y1j+V13+Z5+p0y+V13+d63+R7+i2R)),"close":$((o5R+V13+Z5+Q5y+L13+F43+Y1R+w2+J3j+d8j+v63+B9j+L2j+N7j+D0j+F43+p4R+z6i.w13+C6+V13+Z5+i2R)),"content":null}
}
);self=Editor[M43][p1];self[(c9j+O8+z6i.X6j)]={"offsetAni":25,"windowPadding":25}
;}
(window,document,jQuery,jQuery[Y7][(k1y+i9j+E5y)]));(function(window,document,$,DataTable){var F5j="enve",m43=';</',v1y='">&',N3R='ose',g6R='ope',U5j='nvel',X4R='D_E',J2='ckgr',c73='Ba',Y7j='velo',z4y='ain',f4R='ope_',U8y='_En',o1y='elop',x83='Env',f1y='per',z3R='ope_W',k3y='ap',J6y='D_',j3j="oun",g5y="city",z8y="style",y5="kg",u63="background",a1='Cont',m4='vel',c1R='D_En',j3="tent",E9j="splayCon",v1R="envelope",self;Editor[M43][v1R]=$[n7R](true,{}
,Editor[(t7j+C1R+I7R)][(z6i.V9j+P4j+E9j+l4y+x8+E5y+E03)],{"init":function(dte){var X="_init";self[(M7j+p2R+z6i.x6j)]=dte;self[X]();return self;}
,"open":function(dte,append,callback){var U6R="_sh",I3y="Chil",M7="chi";self[(a03)]=dte;$(self[(r9y+i2j+p5j)][(p4y+z6i.W5j+j3)])[(M7+z6i.S8j+z9)]()[(z6i.V9j+A33+a6y)]();self[(M7j+B0)][(c9j+O8+z6i.w03+P9)][(m7j+B0y+I3y+z6i.V9j)](append);self[i13][(c9j+i2j+z6i.W5j+z6i.w03+z6i.x6j+d43)][(l73+h2j+z6i.x6j+z6i.W5j+z6i.V9j+A7R+m3R+O8y)](self[(i13)][(z3+s3)]);self[(U6R+u0y)](callback);}
,"close":function(dte,callback){self[(r9y+h7y)]=dte;self[(M7j+m3R+C1R)](callback);}
,node:function(dte){return self[i13][(Y73+Z4j+C0)][0];}
,"_init":function(){var y2y="visbil",e4="rou",R8j='ty',X3j='ci',F9R='opa',E1y="groundO",H4j="sB",V03='hi',V73="ili",Q7R="isb",c3R="Child",o0="body",u1='e_';if(self[(M7j+E03+o5+z73)]){return ;}
self[(r9y+u8)][(c9j+i2j+z6i.W5j+z6i.w03+O5j+z6i.w03)]=$((V13+d63+R7+w7R+J3j+f73+c1R+m4+F6R+u1+a1+P73+j6+z6i.w13+V0),self[(M7j+z6i.V9j+i2j+p5j)][(U1+z6i.S1j+h2j+Y6y+E03)])[0];document[o0][(l73+h2j+B0y+c3R)](self[i13][u63]);document[(i9j+o9+z73)][(z6i.S1j+c2y+O5j+M3y+c4j+O9j+z6i.V9j)](self[i13][Z4R]);self[(M7j+Y8R+p5j)][(i9j+X8j+y5+L73+e6y)][z8y][(k33+Q7R+V73+z6i.w03+z73)]=(V03+V13+V13+H5);self[i13][u63][z8y][(x6R+e6+G)]='block';self[(u9y+j03+H4j+X8j+E8j+E1y+s1y+g5y)]=$(self[(M7j+z6i.V9j+i2j+p5j)][u63])[(c9j+N4)]((F9R+X3j+R8j));self[(i13)][(i9j+L4y+K9y+j2+x33)][(j03+o2y+z6i.S8j+z6i.x6j)][(x6R+j03+S8y+z6i.S1j+z73)]='none';self[(M7j+B0)][(i9j+L4y+w6j+e4+z6i.W5j+z6i.V9j)][z8y][(y2y+G8j+z73)]='visible';}
,"_show":function(callback){var x8R='lop',E3R='_E',h3='TED_En',y2j='clic',k0y='ontent',q4y="roun",K33="nte",s3R="ding",v0y="Hei",u13="windowScroll",M6R="rappe",p9j="_cssBackgroundOpacity",z7R="yl",B43="ackgr",X03="offsetHeight",n6="marginLeft",T3R="px",p93="tyle",B7R="etWid",z1="fs",H0y="_heightCalc",b7y="_findAttachRow",Y6j="opacity",g0R='uto',that=this,formHeight;if(!callback){callback=function(){}
;}
self[(M7j+z6i.V9j+u8)][(p4y+z6i.W5j+h7y+z6i.W5j+z6i.w03)][z8y].height=(P73+g0R);var style=self[(M7j+z6i.V9j+u8)][(U1+m7j+z6i.x6j+E03)][z8y];style[Y6j]=0;style[(z6i.V9j+P4j+e6+z6i.S8j+z6i.S1j+z73)]='block';var targetRow=self[b7y](),height=self[H0y](),width=targetRow[(i2j+z6i.X6j+z1+B7R+U1y)];style[M43]='none';style[Y6j]=1;self[i13][Z4R][(j03+p93)].width=width+(T3R);self[i13][(U1+Q6R+E03)][z8y][n6]=-(width/2)+(T3R);self._dom.wrapper.style.top=($(targetRow).offset().top+targetRow[X03])+"px";self._dom.content.style.top=((-1*height)-20)+"px";self[(r9y+u8)][(i9j+z6i.S1j+c9j+E8j+K9y+j3j+z6i.V9j)][z8y][(i2j+s1y+g5y)]=0;self[i13][(i9j+B43+i2j+B33+z6i.W5j+z6i.V9j)][(j03+z6i.w03+z7R+z6i.x6j)][M43]='block';$(self[i13][u63])[y8y]({'opacity':self[p9j]}
,(W1y+T0y+U0y));$(self[i13][(Y73+M6R+E03)])[w3R]();if(self[(J9y)][u13]){$('html,body')[y8y]({"scrollTop":$(targetRow).offset().top+targetRow[(v03+R2j+v0y+G0y+z6i.w03)]-self[(c9j+U43)][(Y73+P4j+z6i.W5j+Y8R+Y73+R8R+a5j+s3R)]}
,function(){$(self[i13][(B6j+h7y+z6i.W5j+z6i.w03)])[y8y]({"top":0}
,600,callback);}
);}
else{$(self[(M7j+Y8R+p5j)][(p4y+K33+d43)])[y8y]({"top":0}
,600,callback);}
$(self[(M7j+B0)][(M9y+i2j+j03+z6i.x6j)])[(H0R)]('click.DTED_Envelope',function(e){self[a03][(R0j)]();}
);$(self[i13][(i9j+X8j+y5+q4y+z6i.V9j)])[H0R]('click.DTED_Envelope',function(e){var G7="backg",N4y="dte";self[(M7j+N4y)][(G7+L73+B33+z6i.W5j+z6i.V9j)]();}
);$((V13+Z5+w7R+J3j+d8j+b3j+J6y+B9j+n1+r93+V63+c9R+D0j+k0y+h5R+V0+P73+T+T+z6i.w13+V0),self[(M7j+B0)][(Y73+E03+l73+h2j+T03)])[(i9j+h1)]((y2j+D63+w7R+J3j+h3+m4+z6i.u83+T+z6i.w13),function(e){var G6R='onte',T3j='En',o33="has";if($(e[(D0y+E03+K0y+z6i.w03)])[(o33+A7R+R6y)]((J3j+f73+J3j+O33+T3j+R7+z6i.w13+I2j+F1j+O33+D0j+G6R+h6y+h5R+V0+k3y+T+z6i.w13+V0))){self[a03][u63]();}
}
);$(window)[H0R]((V0+l2+d63+c1+z6i.w13+w7R+J3j+d8j+P4y+E3R+t43+j9+x8R+z6i.w13),function(){self[H0y]();}
);}
,"_heightCalc":function(){var B63="He",S93='maxHe',X4y='_Cont',I1='_Bod',w9j='ote',F8y='TE_F',T9j="terHe",i0y="ghtC",H43="hei",X0="heightCalc",formHeight;formHeight=self[J9y][X0]?self[(p4y+z6i.W5j+z6i.X6j)][(H43+i0y+Y33+c9j)](self[i13][Z4R]):$(self[i13][P3R])[Q3y]().height();var maxHeight=$(window).height()-(self[(J9y)][x7]*2)-$('div.DTE_Header',self[(M7j+z6i.V9j+u8)][(Y73+g9)])[(j2+T9j+W1j+Q4R)]()-$((V13+d63+R7+w7R+J3j+F8y+z6i.u83+w9j+V0),self[(M7j+z6i.V9j+u8)][Z4R])[J03]();$((V13+Z5+w7R+J3j+f73+I1+i1+X4y+E7j),self[i13][Z4R])[n43]((S93+d63+x5R+J3),maxHeight);return $(self[(M7j+z6i.V9j+h7y)][(z6i.V9j+u8)][(U93+h2j+T03)])[(i2j+B33+z6i.w03+T03+B63+P4j+u7R)]();}
,"_hide":function(callback){var g3R='ize',S4='res',H7="bin",U2j='ppe',U0j='Wra',Y="unbi",I6j="ckg",L7="tH",Q0y="ffse",S9y="nim";if(!callback){callback=function(){}
;}
$(self[(M7j+z6i.V9j+i2j+p5j)][(B6j+j3)])[(z6i.S1j+S9y+z6i.S1j+z6i.w03+z6i.x6j)]({"top":-(self[(r9y+u8)][P3R][(i2j+Q0y+L7+D4j+u7R)]+50)}
,600,function(){var A9y="fadeOut";$([self[i13][Z4R],self[(i13)][(O0+I6j+E03+i2j+e6y)]])[(A9y)]((t43+f1+P73+F43),callback);}
);$(self[(r9y+i2j+p5j)][R0j])[(Y+z6i.W5j+z6i.V9j)]('click.DTED_Lightbox');$(self[(i13)][(i9j+z6i.S1j+I6j+E03+j3j+z6i.V9j)])[n1R]('click.DTED_Lightbox');$((V13+d63+R7+w7R+J3j+f73+J6y+T4y+r93+N7j+a1+z6i.w13+t43+J3+O33+U0j+U2j+V0),self[(r9y+u8)][(m8+E03)])[(D4R+H7+z6i.V9j)]((L13+E1+D63+w7R+J3j+z2R+d63+x5R+J3+F7R+X7));$(window)[(D4R+i9j+j6j+z6i.V9j)]((S4+g3R+w7R+J3j+d8j+b3j+J3j+O33+w7y+J4R+x4));}
,"_findAttachRow":function(){var T73="ttac",dt=$(self[a03][j03][(D0y+i9j+E5y)])[(Z7R+X93+L4j+i9j+z6i.S8j+z6i.x6j)]();if(self[J9y][(z6i.S1j+T73+c4j)]===(r93+z6i.w13+D8)){return dt[l13]()[(c4j+o5+z6i.x6j+E03)]();}
else if(self[(M7j+p2R+z6i.x6j)][j03][(X8j+I1y+i2j+z6i.W5j)]===(p6j+p9+J3+z6i.w13)){return dt[(D0y+i9j+z6i.S8j+z6i.x6j)]()[(c4j+z6i.x6j+a5j+T03)]();}
else{return dt[(E03+u0y)](self[(M7j+z6i.V9j+z6i.w03+z6i.x6j)][j03][(p5j+o9+P4j+c0+T03)])[(z6i.W5j+w5R)]();}
}
,"_dte":null,"_ready":false,"_cssBackgroundOpacity":1,"_dom":{"wrapper":$((o5R+V13+d63+R7+Q5y+L13+l7y+q0+w2+J3j+f73+J3j+Q5y+J3j+e1R+b3j+t43+j9+F43+z3R+V0+k3y+f1y+r9)+(o5R+V13+d63+R7+Q5y+L13+v9j+q0+q0+w2+J3j+d8j+P4y+O33+x83+o1y+z6i.w13+q4R+r93+P73+x1j+C6+V13+d63+R7+i2R)+(o5R+V13+Z5+Q5y+L13+F43+Y1R+w2+J3j+d8j+b3j+J3j+U8y+j9+F43+f4R+D0j+k9R+J3+z4y+z6i.w13+V0+C6+V13+d63+R7+i2R)+(y9+V13+d63+R7+i2R))[0],"background":$((o5R+V13+Z5+Q5y+L13+m9R+w2+J3j+f73+c1R+Y7j+F1j+O33+c73+J2+z6i.u83+P3+t43+V13+Y1j+V13+Z5+p0y+V13+d63+R7+i2R))[0],"close":$((o5R+V13+Z5+Q5y+L13+v9j+s1R+w2+J3j+f73+X4R+U5j+g6R+O33+D0j+F43+N3R+v1y+J3+c6+l2+m43+V13+Z5+i2R))[0],"content":null}
}
);self=Editor[(x13+S8y+z6i.S1j+z73)][(F5j+d3R+h2j+z6i.x6j)];self[J9y]={"windowPadding":50,"heightCalc":null,"attach":(E03+u0y),"windowScroll":true}
;}
(window,document,jQuery,jQuery[(z6i.X6j+z6i.W5j)][(z6i.V9j+z6i.S1j+z6i.w4+G7y)]));Editor.prototype.add=function(cfg,after){var i1j="if",I5y='tF',I4R="aSou",Z6="xis",e33="read",y9j="'. ",z63="ddin",C7="` ",u9R=" `",g8="equi",j1j="nam";if($[p03](cfg)){for(var i=0,iLen=cfg.length;i<iLen;i++){this[(a5j+z6i.V9j)](cfg[i]);}
}
else{var name=cfg[(j1j+z6i.x6j)];if(name===undefined){throw (n6y+E03+i2j+E03+M2+z6i.S1j+P1R+P4j+h73+M2+z6i.X6j+P4j+U1R+I9y+j5R+K3R+M2+z6i.X6j+P4j+z6i.x6j+z6i.S8j+z6i.V9j+M2+E03+g8+E03+z6i.x6j+j03+M2+z6i.S1j+u9R+z6i.W5j+z6i.S1j+z6i.b2R+C7+i2j+U0R+P4j+i2j+z6i.W5j);}
if(this[j03][(z6i.X6j+P7j+O8y+j03)][name]){throw (G7R+E03+E03+S5+M2+z6i.S1j+z63+w6j+M2+z6i.X6j+W9j+F9)+name+(y9j+C3R+M2+z6i.X6j+P7j+O8y+M2+z6i.S1j+z6i.S8j+e33+z73+M2+z6i.x6j+Z6+z6i.w03+j03+M2+Y73+P4j+z6i.w03+c4j+M2+z6i.w03+c4j+C8j+M2+z6i.W5j+z6i.S1j+p5j+z6i.x6j);}
this[(q2+z6i.w03+I4R+E03+c9j+z6i.x6j)]((j6+d63+I5y+r3R),cfg);this[j03][(c0+D0R)][name]=new Editor[n3j](cfg,this[w0][L3R],this);if(after===undefined){this[j03][z7j][l6R](name);}
else if(after===null){this[j03][(i2j+E03+Z63)][(D4R+j03+c4j+i1j+z6i.w03)](name);}
else{var idx=$[y4j](after,this[j03][(i2j+E03+C1R+E03)]);this[j03][z7j][D2R](idx+1,0,name);}
}
this[(M7j+x6R+j03+h2j+z6i.S8j+i43+f8R+z6i.x6j+S5+z6i.V9j+z6i.x6j+E03)](this[(S5+Z63)]());return this;}
;Editor.prototype.background=function(){var d1j="kground",X1j="onB",l2R="itOp",onBackground=this[j03][(Z6j+l2R+z6i.o8y)][(X1j+z6i.S1j+c9j+d1j)];if(typeof onBackground==='function'){onBackground(this);}
else if(onBackground===(z6i.w73+F43+P3+V0)){this[(c9+B33+E03)]();}
else if(onBackground===(L13+F43+z6i.u83+V5y)){this[(z3+s3)]();}
else if(onBackground===(q0+P3+z6i.w73+W43+v8)){this[(g+G8j)]();}
return this;}
;Editor.prototype.blur=function(){var f0="_blur";this[f0]();return this;}
;Editor.prototype.bubble=function(cells,fieldNames,show,opts){var Y5y='bb',M9R='bu',X6R="include",t6j="ocus",k6j="sit",R43="click",w9R="ick",b7R="prepen",G1="rmI",d4R="epend",H9="messag",k2R="ormE",e93="hil",L1R="child",V3R='icat',X3y='g_Ind',B3y='ocessi',N6R='_P',e5R="leN",z93='dual',H4='vi',w5j="bble",o8j="bub",that=this;if(this[L5y](function(){that[(o8j+i9j+z6i.S8j+z6i.x6j)](cells,fieldNames,opts);}
)){return this;}
if($[m1R](fieldNames)){opts=fieldNames;fieldNames=undefined;show=true;}
else if(typeof fieldNames==='boolean'){show=fieldNames;fieldNames=undefined;opts=undefined;}
if($[m1R](show)){opts=show;show=true;}
if(show===undefined){show=true;}
opts=$[(z6i.x6j+v73+h7y+x33)]({}
,this[j03][(u8R+p5j+s4R+h2j+z6i.w03+Q4j+z6i.W5j+j03)][(i9j+B33+w5j)],opts);var editFields=this[a4j]((j6+V13+d63+H4+z93),cells,fieldNames);this[(M7j+Z6j+G8j)](cells,editFields,(z6i.w73+P3+z6i.w73+Y3R+z6i.w13));var namespace=this[I](opts),ret=this[(r2y+E03+z6i.x6j+u0R+z6i.W5j)]((z6i.w73+H03+Y3R+z6i.w13));if(!ret){return this;}
$(window)[(i2j+z6i.W5j)]((V0+l2+d63+c1+z6i.w13+w7R)+namespace,function(){var g7R="bubblePosition";that[g7R]();}
);var nodes=[];this[j03][(i9j+J9R+e5R+o9+l03)]=nodes[R4y][(l73+S8y+z73)](nodes,_pluck(editFields,(P73+e6j+P73+L13+r93)));var classes=this[w0][M9j],background=$((o5R+V13+Z5+Q5y+L13+F43+P73+q0+q0+w2)+classes[(i9j+w6j)]+(Y1j+V13+d63+R7+p0y+V13+d63+R7+i2R)),container=$('<div class="'+classes[(Y73+g9)]+(r9)+'<div class="'+classes[(z6i.S8j+j6j+z6i.x6j+E03)]+(r9)+(o5R+V13+d63+R7+Q5y+L13+m9R+w2)+classes[l13]+(r9)+(o5R+V13+d63+R7+Q5y+L13+m9R+w2)+classes[(R0j)]+(y0R)+(o5R+V13+Z5+Q5y+L13+F43+P73+q0+q0+w2+J3j+f73+N6R+V0+B3y+t43+X3y+V3R+z6i.u83+V0+Y1j+q0+T+P73+t43+S6R+V13+d63+R7+i2R)+(y9+V13+d63+R7+i2R)+(y9+V13+Z5+i2R)+(o5R+V13+d63+R7+Q5y+L13+F43+Y1R+w2)+classes[(h2j+X5R+z6i.w03+T03)]+(y0R)+'</div>');if(show){container[R1R]('body');background[R1R]('body');}
var liner=container[Q3y]()[(z6i.x6j+k2j)](0),table=liner[(L1R+d5j+z6i.W5j)](),close=table[(c9j+e93+z9)]();liner[(l73+Q2+z6i.V9j)](this[(Y8R+p5j)][(z6i.X6j+k2R+W33)]);table[(N2y+z6i.x6j+h2j+B0y)](this[(z6i.V9j+i2j+p5j)][R63]);if(opts[(H9+z6i.x6j)]){liner[(h2j+E03+d4R)](this[B0][(z6i.X6j+i2j+G1+z6i.W5j+c7)]);}
if(opts[(I1y+z6i.w03+z6i.S8j+z6i.x6j)]){liner[(b7R+z6i.V9j)](this[(z6i.V9j+i2j+p5j)][a43]);}
if(opts[y6]){table[o6y](this[(z6i.V9j+u8)][(w8+a4R+f63)]);}
var pair=$()[p6R](container)[(p6R)](background);this[C9R](function(submitComplete){var E93="mate";pair[(a73+P4j+E93)]({opacity:0}
,function(){var e7="cI",a63="ami",x4y="arDyn",m1="etac";pair[(z6i.V9j+m1+c4j)]();$(window)[(i2j+h)]((r8+J0R+c1+z6i.w13+w7R)+namespace);that[(M7j+M9y+z6i.x6j+x4y+a63+e7+w33+i2j)]();}
);}
);background[(M9y+w9R)](function(){that[x73]();}
);close[R43](function(){that[(u9y+d3R+s3)]();}
);this[(o8j+i9j+E5y+R8R+i2j+k6j+P4j+O8)]();pair[y8y]({opacity:1}
);this[(M7j+z6i.X6j+t6j)](this[j03][(X6R+n3j+j03)],opts[g33]);this[(r2y+i2j+j03+V0j+z6i.x6j+z6i.W5j)]((M9R+Y5y+F43+z6i.w13));return this;}
;Editor.prototype.bubblePosition=function(){var m4R='eft',O03="idt",u7j="rW",m1y="oute",Y63="right",J1y="bott",L9="ft",g1R="bot",Z5R="Node",u4y='bble',d3='Bu',c0R='_B',wrapper=$((V13+Z5+w7R+J3j+f73+c0R+P3+z6i.w73+z6i.w73+F43+z6i.w13)),liner=$((p+w7R+J3j+d8j+b3j+O33+d3+u4y+z1R+w0j+V0)),nodes=this[j03][(w8+i9j+i9j+z6i.S8j+z6i.x6j+Z5R+j03)],position={top:0,left:0,right:0,bottom:0}
;$[w4j](nodes,function(i,node){var z1j="offsetWidth",Z8j="lef",h7j="offse",pos=$(node)[(h7j+z6i.w03)]();node=$(node)[V9R](0);position.top+=pos.top;position[u8y]+=pos[(Z8j+z6i.w03)];position[(M2j+G0y+z6i.w03)]+=pos[(E5y+z6i.X6j+z6i.w03)]+node[z1j];position[(g1R+z6i.w03+i2j+p5j)]+=pos.top+node[(R6+z6i.X6j+j03+z6i.x6j+z6i.w03+Y9R+D4j+w6j+c4j+z6i.w03)];}
);position.top/=nodes.length;position[(z6i.S8j+z6i.x6j+L9)]/=nodes.length;position[(E03+P4j+G0y+z6i.w03)]/=nodes.length;position[(J1y+u8)]/=nodes.length;var top=position.top,left=(position[(z6i.S8j+z6i.x6j+z6i.X6j+z6i.w03)]+position[Y63])/2,width=liner[(m1y+u7j+O03+c4j)](),visLeft=left-(width/2),visRight=visLeft+width,docWidth=$(window).width(),padding=15,classes=this[w0][(i9j+f3R+E63)];wrapper[(n43)]({top:top,left:left}
);if(liner.length&&liner[(v03+j03+z6i.x6j+z6i.w03)]().top<0){wrapper[(c9j+N4)]((J3+F6R),position[(g1R+z6i.w03+u8)])[(B73+z6i.S8j+z6i.S1j+j03+j03)]('below');}
else{wrapper[(d5j+p5j+q8R+t7y+j03+j03)]((z6i.w73+z6i.w13+F43+j8R));}
if(visRight+padding>docWidth){var diff=visRight-docWidth;liner[n43]('left',visLeft<padding?-(visLeft-padding):-(diff+padding));}
else{liner[(n43)]((F43+m4R),visLeft<padding?-(visLeft-padding):0);}
return this;}
;Editor.prototype.buttons=function(buttons){var T4j="sArray",that=this;if(buttons==='_basic'){buttons=[{text:this[U7][this[j03][(X8j+K3y+z6i.W5j)]][(g+G8j)],action:function(){this[(R8+S9+G8j)]();}
}
];}
else if(!$[(P4j+T4j)](buttons)){buttons=[buttons];}
$(this[(z6i.V9j+i2j+p5j)][(i9j+K2R+z6i.w03+i2j+z6i.W5j+j03)]).empty();$[(z6i.x6j+a6y)](buttons,function(i,btn){var W5="pre",o7R='ress',m8j="bIndex",z6="className";if(typeof btn==='string'){btn={text:btn,action:function(){this[(x7j+p5j+P4j+z6i.w03)]();}
}
;}
var text=btn[R9y]||btn[H2R],action=btn[u6R]||btn[(z6i.X6j+z6i.W5j)];$((o5R+z6i.w73+P3+J3+S63+q4),{'class':that[(c9j+R6y+l03)][(z6i.X6j+i2j+E03+p5j)][d13]+(btn[z6]?' '+btn[z6]:'')}
)[(Q4R+a7j)](typeof text==='function'?text(that):text||'')[G2y]('tabindex',btn[(z6i.w03+z6i.S1j+i9j+v9R+x33+z6i.x6j+v73)]!==undefined?btn[(D0y+m8j)]:0)[(O8)]((b9R+i1+I63),function(e){var T7="Cod";if(e[(E8j+z6i.x6j+z73+T7+z6i.x6j)]===13&&action){action[(b3y+e0R)](that);}
}
)[(O8)]((D63+z6i.w13+i1+T+o7R),function(e){var O="De";if(e[u43]===13){e[(W5+I9j+d43+O+z6i.X6j+z6i.S1j+B33+K1R)]();}
}
)[(O8)]((q7j+r3+D63),function(e){var Q93="efault",G1R="entD";e[(W5+k33+G1R+Q93)]();if(action){action[q6R](that);}
}
)[R1R](that[B0][y6]);}
);return this;}
;Editor.prototype.clear=function(fieldName){var L3y="clude",A9R="estroy",that=this,fields=this[j03][(z6i.X6j+s0+q5R)];if(typeof fieldName===(q0+z9j+N1j)){that[(z6i.X6j+s0+z6i.V9j)](fieldName)[(z6i.V9j+A9R)]();delete  fields[fieldName];var orderIdx=$[y4j](fieldName,this[j03][z7j]);this[j03][(i2j+e8j+z6i.x6j+E03)][(j03+Z6R+X7y)](orderIdx,1);var includeIdx=$[(j6j+C3R+B13+z6i.S1j+z73)](fieldName,this[j03][(j6j+L3y+p1R+P4j+z6i.x6j+O8y+j03)]);if(includeIdx!==-1){this[j03][g93][D2R](includeIdx,1);}
}
else{$[w4j](this[d5](fieldName),function(i,name){that[(M9y+z6i.x6j+q13)](name);}
);}
return this;}
;Editor.prototype.close=function(){var a93="_clo";this[(a93+j03+z6i.x6j)](false);return this;}
;Editor.prototype.create=function(arg1,arg2,arg3,arg4){var c6j="rmOpt",v2='initCreat',G33="_displayR",y9y="ditF",T43='mb',O6y='nu',c4="idy",that=this,fields=this[j03][(z6i.X6j+P7j+z6i.S8j+z6i.V9j+j03)],count=1;if(this[(Q3R+c4)](function(){that[S2j](arg1,arg2,arg3,arg4);}
)){return this;}
if(typeof arg1===(O6y+T43+z6i.w13+V0)){count=arg1;arg1=arg2;arg2=arg3;}
this[j03][(z6i.x6j+z6i.V9j+P4j+S3+P7j+z6i.S8j+q5R)]={}
;for(var i=0;i<count;i++){this[j03][(z6i.x6j+y9y+P7j+z6i.S8j+z6i.V9j+j03)][i]={fields:this[j03][i2y]}
;}
var argOpts=this[(u9y+E03+B33+z6i.V9j+C3R+E03+w6j+j03)](arg1,arg2,arg3,arg4);this[j03][(t7j+z6i.V9j+z6i.x6j)]=(W43+P73+j6);this[j03][(z6i.S1j+U5y+Q4j+z6i.W5j)]="create";this[j03][u73]=null;this[B0][R63][(g4+z73+z6i.S8j+z6i.x6j)][(z6i.V9j+C8j+h2j+G)]=(z6i.w73+F43+J6R);this[(q7y+K3y+c5R+u2+j03)]();this[(G33+z6i.x6j+z7j)](this[i2y]());$[(w4j)](fields,function(name,field){var T6j="iSe";field[(y6j+K1R+O1R+j03+z6i.x6j+z6i.w03)]();for(var i=0;i<count;i++){field[(p5j+B33+z6i.S8j+z6i.w03+T6j+z6i.w03)](i,field[(C1R+z6i.X6j)]());}
field[R2j](field[(z6i.V9j+S6j)]());}
);this[g0y]((v2+z6i.w13));this[(M7j+z6i.S1j+Z0y+p5j+i9j+E5y+m6R+A03+z6i.W5j)]();this[(k6y+i2j+c6j+Q4j+f63)](argOpts[(i2j+h2j+z6i.o8y)]);argOpts[b0R]();return this;}
;Editor.prototype.dependent=function(parent,url,opts){var D2y="event";if($[p03](parent)){for(var i=0,ien=parent.length;i<ien;i++){this[(z6i.V9j+z6i.x6j+Y6y+h9+z6i.W5j+z6i.w03)](parent[i],url,opts);}
return this;}
var that=this,field=this[(z6i.X6j+P4j+z6i.x6j+O8y)](parent),ajaxOpts={type:(d1y),dataType:(z6i.b63+q0+z6i.u83+t43)}
;opts=$[(z6i.x6j+v73+z6i.w03+B0y)]({event:(L13+r93+P73+t43+c8R),data:null,preUpdate:null,postUpdate:null}
,opts);var update=function(json){var g9y="pd",e9y="pos",u1y="tUp",z0='ble',k9j="preUpdate";if(opts[(N2y+z6i.x6j+S1+z6i.V9j+z6i.S1j+z6i.w03+z6i.x6j)]){opts[k9j](json);}
$[w4j]({labels:'label',options:'update',values:'val',messages:'message',errors:(z6i.w13+V0+V0+z6i.u83+V0)}
,function(jsonProp,fieldFn){if(json[jsonProp]){$[w4j](json[jsonProp],function(field,val){that[L3R](field)[fieldFn](val);}
);}
}
);$[(z6i.x6j+z6i.S1j+c9j+c4j)](['hide',(q0+r93+j8R),'enable',(V13+d8+P73+z0)],function(i,key){if(json[key]){that[key](json[key]);}
}
);if(opts[(w5y+j03+u1y+z6i.V9j+z6i.S1j+z6i.w03+z6i.x6j)]){opts[(e9y+V4+g9y+S1y)](json);}
}
;$(field[C0R]())[(O8)](opts[D2y],function(e){var J63='un',t9y="values";if($(field[C0R]())[(z6i.X6j+P4j+z6i.W5j+z6i.V9j)](e[(D0y+E03+V9R)]).length===0){return ;}
var data={}
;data[(H93)]=that[j03][(S3R+V6y+O8y+j03)]?_pluck(that[j03][(z6i.x6j+x6R+S3+P7j+z6i.S8j+q5R)],(V13+j73)):null;data[(T8)]=data[H93]?data[H93][0]:null;data[(t9y)]=that[s73]();if(opts.data){var ret=opts.data(data);if(ret){opts.data=ret;}
}
if(typeof url===(o93+J63+L13+U3j+k9R)){var o=url(field[s73](),data,update);if(o){update(o);}
}
else{if($[m1R](url)){$[(r7j+O5j+z6i.V9j)](ajaxOpts,url);}
else{ajaxOpts[(E5R+z6i.S8j)]=url;}
$[(z6i.S1j+R1j)]($[(z6i.x6j+v73+z6i.w03+O5j+z6i.V9j)](ajaxOpts,{url:url,data:data,success:update}
));}
}
);return this;}
;Editor.prototype.destroy=function(){var i7j="qu",P2R="uni",h5="roy",k2y="troll",y1y="yCon",j3R="clear",t8="displayed";if(this[j03][t8]){this[R0j]();}
this[j3R]();var controller=this[j03][(z6i.V9j+P4j+N9y+z6i.S1j+y1y+k2y+z6i.x6j+E03)];if(controller[(C1R+j03+z6i.w03+E03+i2j+z73)]){controller[(z6i.V9j+z6i.x6j+j03+z6i.w03+h5)](this);}
$(document)[(i2j+h)]((w7R+V13+w2R)+this[j03][(P2R+i7j+z6i.x6j)]);this[(z6i.V9j+i2j+p5j)]=null;this[j03]=null;}
;Editor.prototype.disable=function(name){var that=this;$[w4j](this[d5](name),function(i,n){that[L3R](n)[(z6i.V9j+C8j+z6i.S1j+E63)]();}
);return this;}
;Editor.prototype.display=function(show){if(show===undefined){return this[j03][(x6R+e6+z6i.S8j+z6i.S1j+z73+z6i.x6j+z6i.V9j)];}
return this[show?(z6i.u83+T+H5):(L13+F43+p4R+z6i.w13)]();}
;Editor.prototype.displayed=function(){return $[x3R](this[j03][(R9+z6i.S8j+z6i.V9j+j03)],function(field,name){return field[(x6R+D1R+Z6j)]()?name:null;}
);}
;Editor.prototype.displayNode=function(){var h93="nod";return this[j03][(z6i.V9j+P4j+e6+V4y+z73+I0y+z6i.w03+E03+C1y+T03)][(h93+z6i.x6j)](this);}
;Editor.prototype.edit=function(items,arg1,arg2,arg3,arg4){var K5="aybeO",G7j="embl",R4="Args",H7R="ud",v33="_cr",that=this;if(this[(M7j+z6i.w03+J7j+z73)](function(){that[(z6i.x6j+x6R+z6i.w03)](items,arg1,arg2,arg3,arg4);}
)){return this;}
var argOpts=this[(v33+H7R+R4)](arg1,arg2,arg3,arg4);this[(M7j+Z6j+P4j+z6i.w03)](items,this[a4j]('fields',items),(W43+P73+d63+t43));this[(M7j+S2y+G7j+z6i.x6j+m6R+z6i.S1j+P4j+z6i.W5j)]();this[I](argOpts[s1]);argOpts[(p5j+K5+Y6y+z6i.W5j)]();return this;}
;Editor.prototype.enable=function(name){var v2R="ldN",a1R="_fi",that=this;$[(z6i.x6j+z6i.S1j+b1y)](this[(a1R+z6i.x6j+v2R+P13+j03)](name),function(i,n){var h1j="enable";that[L3R](n)[h1j]();}
);return this;}
;Editor.prototype.error=function(name,msg){if(msg===undefined){this[(c5y+z6i.x6j+j03+j03+T3y)](this[(B0)][(z6i.X6j+e63+G7R+B13+S5)],name);}
else{this[(z6i.X6j+W9j)](name).error(msg);}
return this;}
;Editor.prototype.field=function(name){var D0='ame',a2y='wn',L8R='kn',fields=this[j03][(z6i.X6j+P4j+D0R)];if(!fields[name]){throw (Q0R+L8R+z6i.u83+a2y+Q5y+o93+d63+z6i.w13+F43+V13+Q5y+t43+D0+U63)+name;}
return fields[name];}
;Editor.prototype.fields=function(){return $[(p5j+l73)](this[j03][(i2y)],function(field,name){return name;}
);}
;Editor.prototype.file=_api_file;Editor.prototype.files=_api_files;Editor.prototype.get=function(name){var that=this;if(!name){name=this[i2y]();}
if($[p03](name)){var out={}
;$[(z6i.x6j+z6i.S1j+b1y)](name,function(i,n){out[n]=that[L3R](n)[(w6j+A33)]();}
);return out;}
return this[L3R](name)[(V9R)]();}
;Editor.prototype.hide=function(names,animate){var k5="_fieldNa",that=this;$[w4j](this[(k5+z6i.b2R+j03)](names),function(i,n){that[L3R](n)[(c4j+P4j+z6i.V9j+z6i.x6j)](animate);}
);return this;}
;Editor.prototype.inError=function(inNames){var F2R="nE",e5j="ames",U6y="dN",G6="ror";if($(this[B0][(z6i.X6j+i2j+C33+G7R+E03+G6)])[(P4j+j03)](':visible')){return true;}
var names=this[(k6y+P7j+z6i.S8j+U6y+e5j)](inNames);for(var i=0,ien=names.length;i<ien;i++){if(this[(L3R)](names[i])[(P4j+F2R+B13+S5)]()){return true;}
}
return false;}
;Editor.prototype.inline=function(cell,fieldName,opts){var Z2="_postopen",f9R="_focus",D7R="formE",v7R='_I',r0='Proc',D4y='lin',Q="_tid",b3R='_F',u8j="lin",k="asse",A63='ual',e4R='divi',a5y="inline",that=this;if($[m1R](fieldName)){opts=fieldName;fieldName=undefined;}
opts=$[n7R]({}
,this[j03][j7][a5y],opts);var editFields=this[a4j]((j6+e4R+V13+A63),cell,fieldName),node,field,countOuter=0,countInner,closed=false,classes=this[(c9j+z6i.S8j+k+j03)][(P4j+z6i.W5j+u8j+z6i.x6j)];$[w4j](editFields,function(i,editField){var I7y="layFie",J7y="disp",N93='Cann';if(countOuter>0){throw (N93+g4R+Q5y+z6i.w13+g13+J3+Q5y+W43+w6R+z6i.w13+Q5y+J3+H5y+Q5y+z6i.u83+t43+z6i.w13+Q5y+V0+j8R+Q5y+d63+t43+v8j+P0y+Q5y+P73+J3+Q5y+P73+Q5y+J3+d63+W43+z6i.w13);}
node=$(editField[A0y][0]);countInner=0;$[(z6i.x6j+a6y)](editField[(J7y+I7y+e13)],function(j,f){if(countInner>0){throw (N93+z6i.u83+J3+Q5y+z6i.w13+V13+v8+Q5y+W43+z6i.u83+V0+z6i.w13+Q5y+J3+H5y+Q5y+z6i.u83+P0y+Q5y+o93+r3R+Q5y+d63+t43+F43+w0j+Q5y+P73+J3+Q5y+P73+Q5y+J3+F3R);}
field=f;countInner++;}
);countOuter++;}
);if($((p+w7R+J3j+f73+b3R+D6y+V13),node).length){return this;}
if(this[(Q+z73)](function(){that[a5y](cell,fieldName,opts);}
)){return this;}
this[(M7j+Z6j+P4j+z6i.w03)](cell,editFields,(j6+D4y+z6i.w13));var namespace=this[I](opts),ret=this[s93]((d63+r7y+j6+z6i.w13));if(!ret){return this;}
var children=node[(B6j+z6i.w03+O5j+z6i.w03+j03)]()[H1R]();node[o6y]($((o5R+V13+d63+R7+Q5y+L13+v9j+s1R+w2)+classes[(U1+z6i.S1j+C0)]+'">'+(o5R+V13+Z5+Q5y+L13+v9j+s1R+w2)+classes[(z6i.S8j+P4j+X33+E03)]+(r9)+(o5R+V13+d63+R7+Q5y+L13+m9R+w2+J3j+e3+r0+z6i.w13+s1R+d63+E3y+v7R+x0y+r3+P73+r1j+V0+Y1j+q0+T+P73+t43+p0y+V13+d63+R7+i2R)+'</div>'+'<div class="'+classes[y6]+(d2)+'</div>'));node[(a8R)]((V13+Z5+w7R)+classes[(z6i.S8j+j6j+z6i.x6j+E03)][s9y](/ /g,'.'))[o6y](field[C0R]())[o6y](this[B0][(D7R+E03+E03+S5)]);if(opts[y6]){node[(c0+z6i.W5j+z6i.V9j)]((V13+d63+R7+w7R)+classes[y6][s9y](/ /g,'.'))[(z6i.S1j+c2y+z6i.x6j+x33)](this[B0][(i9j+B33+z6i.w03+w6y+z6i.W5j+j03)]);}
this[C9R](function(submitComplete){var D6R="rD",Y83="_cle",p0R="contents";closed=true;$(document)[(i2j+h)]('click'+namespace);if(!submitComplete){node[p0R]()[H1R]();node[(l73+h2j+B0y)](children);}
that[(Y83+z6i.S1j+D6R+z73+z6i.W5j+z6i.S1j+M0j+c9j+v9R+w33+i2j)]();}
);setTimeout(function(){if(closed){return ;}
$(document)[(i2j+z6i.W5j)]((L13+E1+D63)+namespace,function(e){var Y3j="Arra",C6y='wns',W6y='Sel',P7R='addBa',b9="dBack",back=$[Y7][(z6i.S1j+z6i.V9j+b9)]?(P7R+L13+D63):(P73+t43+V13+W6y+o93);if(!field[j2j]((z6i.u83+C6y),e[d5y])&&$[(j6j+Y3j+z73)](node[0],$(e[(z6i.w03+z6i.S1j+A2j+z6i.x6j+z6i.w03)])[(h2j+z6i.S1j+d5j+z6i.W5j+z6i.o8y)]()[back]())===-1){that[(i9j+z6i.S8j+B33+E03)]();}
}
);}
,0);this[f9R]([field],opts[(z6i.X6j+l1+B33+j03)]);this[Z2]((M1j+d63+t43+z6i.w13));return this;}
;Editor.prototype.message=function(name,msg){var h2y="mI",O0y="_message";if(msg===undefined){this[O0y](this[(z6i.V9j+u8)][(u8R+h2y+z6i.W5j+z6i.X6j+i2j)],name);}
else{this[(z6i.X6j+P7j+O8y)](name)[X0j](msg);}
return this;}
;Editor.prototype.mode=function(mode){var I43='ode',l6='ting',k43='entl',p43='urr',u2R='Not';if(!mode){return this[j03][u6R];}
if(!this[j03][(z6i.S1j+c9j+z6i.w03+P4j+i2j+z6i.W5j)]){throw (u2R+Q5y+L13+p43+k43+i1+Q5y+d63+t43+Q5y+P73+t43+Q5y+z6i.w13+g13+l6+Q5y+W43+I43);}
this[j03][(X8j+z6i.w03+P4j+O8)]=mode;return this;}
;Editor.prototype.modifier=function(){return this[j03][(p5j+i2j+x6R+c0+z6i.x6j+E03)];}
;Editor.prototype.multiGet=function(fieldNames){var U3R="iG",that=this;if(fieldNames===undefined){fieldNames=this[i2y]();}
if($[(C8j+C3R+E03+g73)](fieldNames)){var out={}
;$[w4j](fieldNames,function(i,name){var n63="multiGet";out[name]=that[(z6i.X6j+P7j+z6i.S8j+z6i.V9j)](name)[n63]();}
);return out;}
return this[L3R](fieldNames)[(p5j+i4R+z6i.w03+U3R+A33)]();}
;Editor.prototype.multiSet=function(fieldNames,val){var q5="multiSet",T7j="nO",that=this;if($[(C8j+R8R+V4y+P4j+T7j+i9j+M4j+z6i.x6j+U5y)](fieldNames)&&val===undefined){$[(M8+c4j)](fieldNames,function(name,value){that[(z6i.X6j+P4j+z6i.x6j+O8y)](name)[(y6j+z6i.S8j+I1y+p5R+z6i.x6j+z6i.w03)](value);}
);}
else{this[L3R](fieldNames)[q5](val);}
return this;}
;Editor.prototype.node=function(name){var that=this;if(!name){name=this[(S5+Z63)]();}
return $[p03](name)?$[(p5j+l73)](name,function(n){return that[(c0+z6i.x6j+z6i.S8j+z6i.V9j)](n)[(z6i.W5j+w5R)]();}
):this[(L3R)](name)[(k93+z6i.V9j+z6i.x6j)]();}
;Editor.prototype.off=function(name,fn){$(this)[(i2j+z6i.X6j+z6i.X6j)](this[a3](name),fn);return this;}
;Editor.prototype.on=function(name,fn){$(this)[O8](this[(M7j+z6i.x6j+k33+O5j+z6i.w03+L4R+z6i.S1j+z6i.b2R)](name),fn);return this;}
;Editor.prototype.one=function(name,fn){$(this)[(i2j+X33)](this[a3](name),fn);return this;}
;Editor.prototype.open=function(){var c2='ai',K1y="sto",g3j="lle",V1y="yR",that=this;this[(M7j+x6R+j03+h2j+V4y+V1y+z6i.x6j+i2j+E03+z6i.V9j+T03)]();this[C9R](function(submitComplete){var D93="playControl";that[j03][(x6R+j03+D93+z6i.S8j+T03)][R0j](that,function(){that[X4j]();}
);}
);var ret=this[s93]('main');if(!ret){return this;}
this[j03][(x6R+e6+V4y+z73+A7R+i2j+z6i.W5j+l4y+i2j+g3j+E03)][(u0R+z6i.W5j)](this,this[B0][Z4R]);this[(M7j+c7+B0R)]($[(x3R)](this[j03][(S5+z6i.V9j+z6i.x6j+E03)],function(name){return that[j03][i2y][name];}
),this[j03][(S3R+E3j+z6i.o8y)][g33]);this[(M7j+h2j+i2j+K1y+Q2)]((W43+c2+t43));return this;}
;Editor.prototype.order=function(set){var F9y="eor",z9y="ayR",n73="ovi",y5y="sor";if(!set){return this[j03][z7j];}
if(arguments.length&&!$[p03](set)){set=Array.prototype.slice.call(arguments);}
if(this[j03][(i2j+e8j+T03)][V2]()[(y5y+z6i.w03)]()[(M4j+i2j+j6j)]('-')!==set[V2]()[(j03+i2j+N13)]()[H2j]('-')){throw (C3R+z6i.S8j+z6i.S8j+M2+z6i.X6j+P7j+e13+Q33+z6i.S1j+x33+M2+z6i.W5j+i2j+M2+z6i.S1j+P1R+G8j+L2R+Y33+M2+z6i.X6j+s0+q5R+Q33+p5j+B33+g4+M2+i9j+z6i.x6j+M2+h2j+E03+n73+C1R+z6i.V9j+M2+z6i.X6j+S5+M2+i2j+E03+z6i.V9j+z6i.x6j+E03+j6j+w6j+b9y);}
$[n7R](this[j03][z7j],set);this[(M7j+x6R+e6+z6i.S8j+z9y+F9y+C1R+E03)]();return this;}
;Editor.prototype.remove=function(items,arg1,arg2,arg3,arg4){var O0j="_assembleMain",P1j='iRem',K5R='Mu',n8R='ov',k7R='tR',A2R="sty",e9="ataS",M2y="rud",that=this;if(this[L5y](function(){that[(i6j+G2+z6i.x6j)](items,arg1,arg2,arg3,arg4);}
)){return this;}
if(items.length===undefined){items=[items];}
var argOpts=this[(u9y+M2y+C3R+E03+U9y)](arg1,arg2,arg3,arg4),editFields=this[(M7j+z6i.V9j+e9+j2+E2)]('fields',items);this[j03][(z6i.S1j+U5y+P4j+O8)]="remove";this[j03][u73]=items;this[j03][h9j]=editFields;this[B0][(R63)][(A2R+z6i.S8j+z6i.x6j)][M43]='none';this[(M7j+z6i.S1j+U5y+P4j+O8+A7R+z6i.S8j+J93+j03)]();this[g0y]((d63+t43+d63+k7R+J5+n8R+z6i.w13),[_pluck(editFields,'node'),_pluck(editFields,(r03+t8R)),items]);this[(M7j+P33+z6i.W5j+z6i.w03)]((j6+v8+K5R+F43+J3+P1j+n8R+z6i.w13),[editFields,items]);this[O0j]();this[I](argOpts[s1]);argOpts[b0R]();var opts=this[j03][G1j];if(opts[(g33)]!==null){$((z6i.w73+P3+J3+J3+k9R),this[(z6i.V9j+u8)][y6])[(z6i.x6j+k2j)](opts[g33])[(p5y+j03)]();}
return this;}
;Editor.prototype.set=function(set,val){var that=this;if(!$[m1R](set)){var o={}
;o[set]=val;set=o;}
$[(z6i.x6j+X8j+c4j)](set,function(n,v){that[(z6i.X6j+P7j+z6i.S8j+z6i.V9j)](n)[R2j](v);}
);return this;}
;Editor.prototype.show=function(names,animate){var V9y="Na",that=this;$[(M8+c4j)](this[(M7j+z6i.X6j+P7j+z6i.S8j+z6i.V9j+V9y+p5j+z6i.x6j+j03)](names),function(i,n){that[L3R](n)[(j03+L9R+Y73)](animate);}
);return this;}
;Editor.prototype.submit=function(successCallback,errorCallback,formatdata,hide){var H6="essi",k8="_pr",R1="si",that=this,fields=this[j03][(z6i.X6j+P4j+t8j+q5R)],errorFields=[],errorReady=0,sent=false;if(this[j03][(h2j+L73+c9j+l03+R1+z6i.W5j+w6j)]||!this[j03][u6R]){return this;}
this[(k8+i2j+c9j+H6+z6i.W5j+w6j)](true);var send=function(){if(errorFields.length!==errorReady||sent){return ;}
sent=true;that[(M7j+R8+S9+G8j)](successCallback,errorCallback,formatdata,hide);}
;this.error();$[(z6i.x6j+z6i.S1j+c9j+c4j)](fields,function(name,field){var X9y="inError";if(field[X9y]()){errorFields[(h2j+B33+j03+c4j)](name);}
}
);$[(z6i.x6j+X8j+c4j)](errorFields,function(i,name){fields[name].error('',function(){errorReady++;send();}
);}
);send();return this;}
;Editor.prototype.template=function(set){var I3="tem";if(set===undefined){return this[j03][(I3+e9j+h7y)];}
this[j03][(h7y+Z1j+V4y+z6i.w03+z6i.x6j)]=$(set);return this;}
;Editor.prototype.title=function(title){var j63='unc',i93="hea",header=$(this[(B0)][(i93+C1R+E03)])[(c9j+m3R+z6i.S8j+z9)]((p+w7R)+this[(c9j+z6i.S8j+J93+j03+l03)][(c4j+Y9j+C1R+E03)][P3R]);if(title===undefined){return header[L5j]();}
if(typeof title===(o93+j63+U3j+z6i.u83+t43)){title=title(this,new DataTable[O2j](this[j03][l13]));}
header[(Q4R+a7j)](title);return this;}
;Editor.prototype.val=function(field,value){var w6="Obje";if(value!==undefined||$[(P4j+j03+R8R+V4y+j6j+w6+c9j+z6i.w03)](field)){return this[(R2j)](field,value);}
return this[(w6j+A33)](field);}
;var apiRegister=DataTable[O2j][c03];function __getInst(api){var S73="oI",ctx=api[(c9j+v2y+v73+z6i.w03)][0];return ctx[(S73+z6i.W5j+G8j)][Z0j]||ctx[(M7j+S3R+i2j+E03)];}
function __setBasic(inst,opts,type,plural){var i8="essa",f5R='emov',K7j='_b';if(!opts){opts={}
;}
if(opts[y6]===undefined){opts[(i9j+B33+z6i.w03+z6i.w03+O8+j03)]=(K7j+i1y+d63+L13);}
if(opts[(z6i.w03+P4j+z6i.w03+E5y)]===undefined){opts[(I1y+T5R)]=inst[U7][type][Z4y];}
if(opts[X0j]===undefined){if(type===(V0+f5R+z6i.w13)){var confirm=inst[U7][type][B7];opts[(z6i.b2R+j03+j03+z6i.S1j+K0y)]=plural!==1?confirm[M7j][s9y](/%d/,plural):confirm['1'];}
else{opts[(p5j+i8+w6j+z6i.x6j)]='';}
}
return opts;}
apiRegister((u6+d63+n6j+f6y),function(){return __getInst(this);}
);apiRegister('row.create()',function(opts){var inst=__getInst(this);inst[(o2R+z6i.S1j+z6i.w03+z6i.x6j)](__setBasic(inst,opts,(L13+V0+p9+J3+z6i.w13)));return this;}
);apiRegister('row().edit()',function(opts){var inst=__getInst(this);inst[S3R](this[0][0],__setBasic(inst,opts,(w+J3)));return this;}
);apiRegister((V0+j8R+q0+v7+z6i.w13+V13+v8+f6y),function(opts){var inst=__getInst(this);inst[(S3R)](this[0],__setBasic(inst,opts,(P9j)));return this;}
);apiRegister('row().delete()',function(opts){var inst=__getInst(this);inst[F1](this[0][0],__setBasic(inst,opts,'remove',1));return this;}
);apiRegister((V0+z6i.u83+n7+q0+v7+V13+z6i.w13+A1j+f6y),function(opts){var I9R="mov",inst=__getInst(this);inst[(E03+z6i.x6j+I9R+z6i.x6j)](this[0],__setBasic(inst,opts,'remove',this[0].length));return this;}
);apiRegister((A0j+F43+F43+v7+z6i.w13+g13+J3+f6y),function(type,opts){var v7y="nObj",h4R="isPl";if(!type){type=(j6+F43+j6+z6i.w13);}
else if($[(h4R+A03+v7y+z6i.x6j+U5y)](type)){opts=type;type=(M1j+d63+P0y);}
__getInst(this)[type](this[0][0],opts);return this;}
);apiRegister((L13+z6i.w13+F43+L33+v7+z6i.w13+L0+f6y),function(opts){__getInst(this)[M9j](this[0],opts);return this;}
);apiRegister('file()',_api_file);apiRegister((A9j+z6i.w13+q0+f6y),_api_files);$(document)[O8]((X7+r93+V0+w7R+V13+J3),function(e,ctx,json){var l6y="iles";if(e[w0y]!=='dt'){return ;}
if(json&&json[(z6i.X6j+P4j+E5y+j03)]){$[(Y9j+b1y)](json[(z6i.X6j+l6y)],function(name,files){Editor[O8R][name]=files;}
);}
}
);Editor.error=function(msg,tn){var A6R='bles',V0y='atata',k0='tps',j13='ati',e0='ore';throw tn?msg+(Q5y+w3j+z6i.u83+V0+Q5y+W43+e0+Q5y+d63+m0y+w6R+W43+j13+k9R+J0y+T+F43+p9+V5y+Q5y+V0+z6i.w13+o93+X2+Q5y+J3+z6i.u83+Q5y+r93+J3+k0+Z2R+V13+V0y+A6R+w7R+t43+z6i.w13+J3+o1R+J3+t43+o1R)+tn:msg;}
;Editor[(o0y+c13)]=function(data,props,fn){var t9="bel",w2y="valu",A1='va',i,ien,dataPoint;props=$[(z6i.x6j+c33+z6i.V9j)]({label:(v9j+V7j),value:(A1+F43+I33)}
,props);if($[(P4j+j03+S5y+Z4j+z73)](data)){for(i=0,ien=data.length;i<ien;i++){dataPoint=data[i];if($[m1R](dataPoint)){fn(dataPoint[props[(w2y+z6i.x6j)]]===undefined?dataPoint[props[(z6i.S8j+z6i.S1j+t9)]]:dataPoint[props[(k33+z6i.S1j+y1R+z6i.x6j)]],dataPoint[props[(V4y+t9)]],i,dataPoint[G2y]);}
else{fn(dataPoint,dataPoint,i);}
}
}
else{i=0;$[(w4j)](data,function(key,val){fn(val,key,i);i++;}
);}
}
;Editor[(v4j+z6i.x6j+v9R+z6i.V9j)]=function(id){return id[s9y](/\./g,'-');}
;Editor[G8R]=function(editor,conf,files,progressCallback,completeCallback){var m9="RL",y8j="sD",U13="onload",Q3j="eRe",y7='hil',O2R='cc',l3R='ror',reader=new FileReader(),counter=0,ids=[],generalError=(J0j+Q5y+q0+X2+X0y+Q5y+z6i.w13+V0+l3R+Q5y+z6i.u83+O2R+P3+n7y+u6+Q5y+n7+y7+z6i.w13+Q5y+P3+T+I2j+D8+d63+t43+I93+Q5y+J3+r93+z6i.w13+Q5y+o93+d63+F43+z6i.w13);editor.error(conf[(E4j)],'');progressCallback(conf,conf[(c0+z6i.S8j+Q3j+z6i.S1j+H8y+p13+z6i.w03)]||"<i>Uploading file</i>");reader[(U13)]=function(e){var w8y='js',P8='lug',U7R="pload",X13="oad",Y9="inOb",U73="sP",i2="ajaxData",r0y='uplo',D6j='act',data=new FormData(),ajax;data[(z6i.S1j+h2j+Q2+z6i.V9j)]((D6j+d63+z6i.u83+t43),'upload');data[o6y]((r0y+D8+w3j+D6y+V13),conf[E4j]);data[(z6i.S1j+h2j+Y6y+x33)]('upload',files[counter]);if(conf[i2]){conf[i2](data);}
if(conf[S9R]){ajax=conf[S9R];}
else if($[(P4j+U73+z6i.S8j+z6i.S1j+Y9+M4j+z6i.x6j+c9j+z6i.w03)](editor[j03][(i5+v73)])){ajax=editor[j03][S9R][(B33+S8y+X13)]?editor[j03][S9R][(B33+U7R)]:editor[j03][(z6i.S1j+R1j)];}
else if(typeof editor[j03][S9R]==='string'){ajax=editor[j03][(P03+z6i.S1j+v73)];}
if(!ajax){throw (F6j+z6i.u83+Q5y+J0j+z6i.b63+P9y+Q5y+z6i.u83+T+J3+r63+Q5y+q0+F1j+L13+d63+o93+W7+V13+Q5y+o93+w6R+Q5y+P3+q6j+z6i.u83+D8+Q5y+T+P8+C7R+d63+t43);}
if(typeof ajax===(h1R+V0+N1j)){ajax={url:ajax}
;}
var submit=false;editor[O8]('preSubmit.DTE_Upload',function(){submit=true;return false;}
);if(typeof ajax.data===(Z3R+t43+L13+J3+r63)){var d={}
,ret=ajax.data(d);if(ret!==undefined&&typeof ret!=='string'){d=ret;}
$[(Y9j+c9j+c4j)](d,function(key,value){data[(Q6R+z6i.W5j+z6i.V9j)](key,value);}
);}
$[(z6i.S1j+Q13+v73)]($[(z6i.x6j+C9y+z6i.x6j+z6i.W5j+z6i.V9j)]({}
,ajax,{type:'post',data:data,dataType:(w8y+z6i.u83+t43),contentType:false,processData:false,xhr:function(){var f7y="onloadend",S6y="onprogress",i6="loa",C6R="hr",k9="Sett",xhr=$[(z6i.S1j+R1j+k9+j6j+w6j+j03)][(v73+C6R)]();if(xhr[(Z8R+i6+z6i.V9j)]){xhr[(B33+h2j+z6i.S8j+X13)][S6y]=function(e){var x93="total",f8j="hCo";if(e[(E5y+h73+z6i.w03+f8j+p5j+j0R+z6i.w03+G7y)]){var percent=(e[(z6i.S8j+x1+z6i.V9j+z6i.x6j+z6i.V9j)]/e[x93]*100)[(z6i.w03+i2j+Q1R+v73+Z6j)](0)+"%";progressCallback(conf,files.length===1?percent:counter+':'+files.length+' '+percent);}
}
;xhr[(Z8R+z6i.S8j+X13)][f7y]=function(e){var z3j="gTe";progressCallback(conf,conf[(h2j+N6j+z3y+P4j+z6i.W5j+z3j+C9y)]||(r6j+V0+w0R+l2+J0R+E3y));}
;}
return xhr;}
,success:function(json){var b8R="readAsDataURL",g2j="tus",h0R="sta",s8j="eldEr",W7y='E_Up',n3R='ubmit',v43='eS';editor[(R6+z6i.X6j)]((b8j+v43+n3R+w7R+J3j+d8j+W7y+K3));editor[(u6y+I9j+z6i.W5j+z6i.w03)]('uploadXhrSuccess',[conf[E4j],json]);if(json[X7R]&&json[X7R].length){var errors=json[(z6i.X6j+P4j+s8j+L73+E03+j03)];for(var i=0,ien=errors.length;i<ien;i++){editor.error(errors[i][E4j],errors[i][(h0R+g2j)]);}
}
else if(json.error){editor.error(json.error);}
else if(!json[(B33+h2j+r5j)]||!json[(Z8R+z6i.S8j+i2j+z6i.S1j+z6i.V9j)][(P4j+z6i.V9j)]){editor.error(conf[(z6i.W5j+P13)],generalError);}
else{if(json[O8R]){$[(Y9j+b1y)](json[O8R],function(table,files){if(!Editor[O8R][table]){Editor[O8R][table]={}
;}
$[n7R](Editor[(c0+z6i.S8j+l03)][table],files);}
);}
ids[(h2j+W6R)](json[G8R][J7j]);if(counter<files.length-1){counter++;reader[b8R](files[counter]);}
else{completeCallback[q6R](editor,ids);if(submit){editor[V3y]();}
}
}
progressCallback(conf);}
,error:function(xhr){editor[g0y]('uploadXhrError',[conf[(E4j)],xhr]);editor.error(conf[(r2j+p5j+z6i.x6j)],generalError);progressCallback(conf);}
}
));}
;reader[(E03+z6i.x6j+a5j+C3R+y8j+c7y+m5R+m9)](files[0]);}
;Editor.prototype._constructor=function(init){var e6R='itC',T3="displayController",J0="tabl",V1j="uniq",n0R='body_',F0R='nte',b33="formContent",t33="events",H9j="nT",O4="TON",D="ool",O6R='"/></',S9j='_i',x0R='ntent',W7j='_c',S7="oot",E6R='oo',x4j='y_',P6="bo",o83="ndicat",l9y='essing',A93="unique",M9="mpla",y4="cyAj",z33="domTable",H33="ajaxUrl",L8y="abl",e7R="db",S2="domT";init=$[n7R](true,{}
,Editor[(z6i.V9j+S6j+z6i.S1j+i4R+z6i.o8y)],init);this[j03]=$[(z6i.x6j+C9y+z6i.x6j+x33)](true,{}
,Editor[(p5j+w5R+I7R)][F5],{table:init[(S2+z6i.S1j+i9j+E5y)]||init[(z6i.w03+z6i.S1j+E63)],dbTable:init[(e7R+j5R+L8y+z6i.x6j)]||null,ajaxUrl:init[H33],ajax:init[S9R],idSrc:init[J5y],dataSource:init[z33]||init[(z6i.w03+z6i.F8j+E5y)]?Editor[n2y][(L7R+z6i.w03+L4j+E63)]:Editor[(L7R+D0y+p5R+i2j+B33+E2+j03)][(Q4R+a7j)],formOptions:init[(z6i.X6j+i2j+C33+E3j+K3y+f63)],legacyAjax:init[(E5y+w6j+z6i.S1j+y4+z6i.S1j+v73)],template:init[(z6i.w03+z6i.x6j+p5j+S8y+S1y)]?$(init[(z6i.w03+z6i.x6j+M9+z6i.w03+z6i.x6j)])[H1R]():null}
);this[(c9j+V4y+j03+v5j)]=$[n7R](true,{}
,Editor[w0]);this[(P4j+n2+z6i.W5j)]=init[U7];Editor[(t7j+z6i.V9j+z6i.x6j+I7R)][F5][A93]++;var that=this,classes=this[w0];this[(z6i.V9j+i2j+p5j)]={"wrapper":$((o5R+V13+d63+R7+Q5y+L13+l7y+q0+w2)+classes[(U1+z6i.S1j+h2j+h2j+z6i.x6j+E03)]+(r9)+(o5R+V13+d63+R7+Q5y+V13+j73+C7R+V13+w2R+C7R+z6i.w13+w2+T+V0+z6i.u83+L13+l9y+y73+L13+F43+i1y+q0+w2)+classes[(h2j+N6j+l03+j03+P4j+h73)][(P4j+o83+S5)]+(Y1j+q0+T+P73+t43+p0y+V13+Z5+i2R)+(o5R+V13+d63+R7+Q5y+V13+B1y+P73+C7R+V13+J3+z6i.w13+C7R+z6i.w13+w2+z6i.w73+a3R+i1+y73+L13+m9R+w2)+classes[(P6+z6i.V9j+z73)][(U1+m7j+T03)]+'">'+(o5R+V13+Z5+Q5y+V13+B1y+P73+C7R+V13+w2R+C7R+z6i.w13+w2+z6i.w73+a3R+x4j+a6+J3+E7j+y73+L13+F43+Y1R+w2)+classes[(i9j+i2j+u3j)][P3R]+(d2)+(y9+V13+Z5+i2R)+(o5R+V13+d63+R7+Q5y+V13+P73+J3+P73+C7R+V13+J3+z6i.w13+C7R+z6i.w13+w2+o93+E6R+J3+y73+L13+F43+i1y+q0+w2)+classes[(c7+i2j+z6i.w03+z6i.x6j+E03)][Z4R]+'">'+(o5R+V13+Z5+Q5y+L13+v9j+s1R+w2)+classes[(z6i.X6j+S7+z6i.x6j+E03)][P3R]+'"/>'+(y9+V13+Z5+i2R)+'</div>')[0],"form":$((o5R+o93+f1+Q5y+V13+P73+J3+P73+C7R+V13+J3+z6i.w13+C7R+z6i.w13+w2+o93+z6i.u83+V0+W43+y73+L13+F43+i1y+q0+w2)+classes[R63][(D0y+w6j)]+(r9)+(o5R+V13+d63+R7+Q5y+V13+B1y+P73+C7R+V13+w2R+C7R+z6i.w13+w2+o93+z6i.u83+T0y+W7j+z6i.u83+x0R+y73+L13+F43+i1y+q0+w2)+classes[(u8R+p5j)][(c9j+v2y+d43)]+'"/>'+(y9+o93+z6i.u83+T0y+i2R))[0],"formError":$((o5R+V13+Z5+Q5y+V13+j73+C7R+V13+w2R+C7R+z6i.w13+w2+o93+f1+O33+z6i.w13+V0+V0+z6i.u83+V0+y73+L13+m9R+w2)+classes[(c7+E03+p5j)].error+'"/>')[0],"formInfo":$((o5R+V13+d63+R7+Q5y+V13+P73+J3+P73+C7R+V13+w2R+C7R+z6i.w13+w2+o93+w6R+W43+S9j+t43+W2y+y73+L13+v9j+s1R+w2)+classes[R63][s8R]+(d2))[0],"header":$('<div data-dte-e="head" class="'+classes[a43][Z4R]+(Y1j+V13+d63+R7+Q5y+L13+F43+Y1R+w2)+classes[a43][(c9j+t2j+P9)]+(O6R+V13+Z5+i2R))[0],"buttons":$((o5R+V13+d63+R7+Q5y+V13+B1y+P73+C7R+V13+J3+z6i.w13+C7R+z6i.w13+w2+o93+f1+O33+z6i.w73+P3+J3+J3+z6i.u83+t43+q0+y73+L13+m9R+w2)+classes[R63][y6]+(d2))[0]}
;if($[Y7][(L7R+z6i.w03+c7j+z6i.S1j+i9j+z6i.S8j+z6i.x6j)][C43]){var ttButtons=$[Y7][(z6i.V9j+X93+z6i.S1j+u9j+c9+z6i.x6j)][(p7y+z6i.S8j+z5R+D+j03)][(q3R+l33+O4+p5R)],i18n=this[(F1y+i7y)];$[(z6i.x6j+X8j+c4j)]([(p6j+p9+J3+z6i.w13),'edit',(z5j+z6i.u83+j9)],function(i,val){ttButtons['editor_'+val][(j03+a3j+a4R+H9j+z6i.x6j+C9y)]=i18n[val][d13];}
);}
$[(z6i.x6j+a6y)](init[t33],function(evt,fn){that[(O8)](evt,function(){var args=Array.prototype.slice.call(arguments);args[p4]();fn[(z6i.S1j+c2y+G9R)](that,args);}
);}
);var dom=this[B0],wrapper=dom[(B5j+h2j+Y6y+E03)];dom[b33]=_editor_el((o93+w6R+W43+O33+a9j+F0R+t43+J3),dom[(c7+C33)])[0];dom[(z6i.X6j+S7+T03)]=_editor_el('foot',wrapper)[0];dom[(i9j+i2j+u3j)]=_editor_el((F7R+v3),wrapper)[0];dom[N6]=_editor_el((n0R+a9j+h6y+z6i.w13+h6y),wrapper)[0];dom[(h2j+E03+l1+z3y+j6j+w6j)]=_editor_el('processing',wrapper)[0];if(init[i2y]){this[(a5j+z6i.V9j)](init[i2y]);}
$(document)[(O8)]((D7j+J3+w7R+V13+J3+w7R+V13+J3+z6i.w13)+this[j03][(V1j+B33+z6i.x6j)],function(e,settings,json){var V6j="_editor",o9y="nTa";if(that[j03][l13]&&settings[(o9y+E63)]===$(that[j03][(J0+z6i.x6j)])[V9R](0)){settings[V6j]=that;}
}
)[O8]((X7+r93+V0+w7R+V13+J3+w7R+V13+J3+z6i.w13)+this[j03][(B33+z6i.W5j+P4j+k2j+r7R)],function(e,settings,json){var I4j="_optionsUpdate";if(json&&that[j03][(J0+z6i.x6j)]&&settings[(H9j+z6i.S1j+i9j+z6i.S8j+z6i.x6j)]===$(that[j03][l13])[V9R](0)){that[I4j](json);}
}
);try{this[j03][T3]=Editor[M43][init[(z6i.V9j+K6y+z6i.S8j+i43)]][(P4j+K13+z6i.w03)](this);}
catch(e){var T63='isp',s6='Cannot';throw (s6+Q5y+o93+j6+V13+Q5y+V13+T63+v4y+Q5y+L13+k9R+z9j+z6i.u83+F43+F43+z6i.w13+V0+Q5y)+init[(z6i.V9j+P4j+j03+h2j+z6i.S8j+i43)];}
this[g0y]((d63+t43+e6R+H9R+T+o4j+w2R),[]);}
;Editor.prototype._actionClass=function(){var r0j="actions",classesActions=this[w0][r0j],action=this[j03][(l3j+L2R)],wrapper=$(this[(Y8R+p5j)][Z4R]);wrapper[l0j]([classesActions[(m4y+Y9j+z6i.w03+z6i.x6j)],classesActions[(z6i.x6j+H13)],classesActions[F1]][(H2j)](' '));if(action===(S2j)){wrapper[A4y](classesActions[S2j]);}
else if(action==="edit"){wrapper[(z6i.S1j+P1R+A7R+z6i.S8j+S2y)](classesActions[S3R]);}
else if(action==="remove"){wrapper[A4y](classesActions[F1]);}
}
;Editor.prototype._ajax=function(data,success,error,submitParams){var u7="ndexO",i5j="param",W5R="Bo",Z13="del",j6y="url",A8="let",x4R="omp",Z4="mple",V6="complete",B03="lit",s0j="creat",d5R="Url",R33="rl",x9="xU",y5j="sF",c8="inO",a9="isP",i3j="xUr",that=this,action=this[j03][(X8j+z6i.w03+L2R)],thrown,opts={type:'POST',dataType:'json',data:null,error:[function(xhr,text,err){thrown=err;}
],success:[],complete:[function(xhr,text){var v0j="eJS";var D9R="res";var q33="SON";var l7R="seJ";var C3j="respo";var J9j='nul';var H3j="nseT";var json=null;if(xhr[(F93)]===204||xhr[(d5j+e6+i2j+H3j+z6i.x6j+C9y)]===(J9j+F43)){json={}
;}
else{try{json=xhr[(C3j+z6i.W5j+l7R+q33)]?xhr[(D9R+h2j+i2j+f63+v0j+s4R+L4R)]:$[(l3+l7R+p5R+s4R+L4R)](xhr[(d5j+j03+w5y+f63+z6i.x6j+j5R+p13+z6i.w03)]);}
catch(e){}
}
if($[m1R](json)||$[(P4j+j03+c1y+z6i.S1j+z73)](json)){success(json,xhr[(j03+D0y+z6i.w03+B33+j03)]>=400,xhr);}
else{error(xhr,text,thrown);}
}
]}
,a,ajaxSrc=this[j03][(S9R)]||this[j03][(z6i.S1j+Q13+i3j+z6i.S8j)],id=action===(u6+v8)||action===(r8+W43+L2)?_pluck(this[j03][h9j],'idSrc'):null;if($[(j0y+E03+E03+z6i.S1j+z73)](id)){id=id[H2j](',');}
if($[(a9+V4y+c8+i9j+M4j+G9j+z6i.w03)](ajaxSrc)&&ajaxSrc[action]){ajaxSrc=ajaxSrc[action];}
if($[(P4j+y5j+D4R+c9j+K3y+z6i.W5j)](ajaxSrc)){var uri=null,method=null;if(this[j03][(i5+x9+R33)]){var url=this[j03][(P03+N63+d5R)];if(url[(s0j+z6i.x6j)]){uri=url[action];}
if(uri[(h1+p13+s4R+z6i.X6j)](' ')!==-1){a=uri[G3R](' ');method=a[0];uri=a[1];}
uri=uri[s9y](/_id_/,id);}
ajaxSrc(method,uri,data,success,error);return ;}
else if(typeof ajaxSrc===(Y93+d63+t43+I93)){if(ajaxSrc[L2y](' ')!==-1){a=ajaxSrc[(j03+h2j+B03)](' ');opts[(z6i.w03+z73+h2j+z6i.x6j)]=a[0];opts[(E5R+z6i.S8j)]=a[1];}
else{opts[(E5R+z6i.S8j)]=ajaxSrc;}
}
else{var optsCopy=$[n7R]({}
,ajaxSrc||{}
);if(optsCopy[(c9j+u8+S8y+z6i.x6j+h7y)]){opts[V6][(B33+z6i.W5j+p4)](optsCopy[(p4y+Z4+h7y)]);delete  optsCopy[(c9j+x4R+A8+z6i.x6j)];}
if(optsCopy.error){opts.error[F5R](optsCopy.error);delete  optsCopy.error;}
opts=$[n7R]({}
,opts,optsCopy);}
opts[(B33+R33)]=opts[(j6y)][s9y](/_id_/,id);if(opts.data){var newData=$[(P4j+y5j+B33+z6i.W5j+c9j+z6i.w03+P4j+O8)](opts.data)?opts.data(data):opts.data;data=$[Q8j](opts.data)&&newData?newData:$[(a1y+z6i.V9j)](true,data,newData);}
opts.data=data;if(opts[(z6i.w03+W9R+z6i.x6j)]==='DELETE'&&(opts[(Z13+A33+z6i.x6j+W5R+u3j)]===undefined||opts[(C1R+A8+z6i.x6j+W5R+u3j)]===true)){var params=$[i5j](opts.data);opts[j6y]+=opts[(j6y)][(P4j+u7+z6i.X6j)]('?')===-1?'?'+params:'&'+params;delete  opts.data;}
$[(P03+N63)](opts);}
;Editor.prototype._assembleMain=function(){var U9R="formInfo",e8y="mE",E0j="oter",U3="prepend",dom=this[(B0)];$(dom[(B5j+h2j+C0y)])[U3](dom[(c4j+o5+T03)]);$(dom[(z6i.X6j+i2j+E0j)])[o6y](dom[(c7+E03+e8y+E03+L73+E03)])[(z6i.S1j+c2y+O5j+z6i.V9j)](dom[(y6)]);$(dom[N6])[o6y](dom[U9R])[(l73+Y6y+x33)](dom[(c7+E03+p5j)]);}
;Editor.prototype._blur=function(){var Q2j="_cl",P0R='preBlur',opts=this[j03][G1j],onBlur=opts[l8j];if(this[(M7j+z6i.x6j+k33+O5j+z6i.w03)]((P0R))===false){return ;}
if(typeof onBlur==='function'){onBlur(this);}
else if(onBlur==='submit'){this[(l93+z6i.w03)]();}
else if(onBlur==='close'){this[(Q2j+i2j+s3)]();}
}
;Editor.prototype._clearDynamicInfo=function(){if(!this[j03]){return ;}
var errorClass=this[(c9j+z6i.S8j+z6i.S1j+N4+l03)][(z6i.X6j+P4j+U1R)].error,fields=this[j03][i2y];$((p+w7R)+errorClass,this[(z6i.V9j+u8)][Z4R])[l0j](errorClass);$[w4j](fields,function(name,field){field.error('')[X0j]('');}
);this.error('')[(H2y+V+K0y)]('');}
;Editor.prototype._close=function(submitComplete){var U4='ody',G3y="cb",y0="oseC",b5y="closeCb";if(this[g0y]('preClose')===false){return ;}
if(this[j03][b5y]){this[j03][(M9y+y0+i9j)](submitComplete);this[j03][b5y]=null;}
if(this[j03][(c9j+d3R+j03+z6i.x6j+v9R+G3y)]){this[j03][(z2j+z6i.x6j+w43)]();this[j03][K4]=null;}
$((z6i.w73+U4))[v03]('focus.editor-focus');this[j03][(x6R+j03+S8y+i43+z6i.x6j+z6i.V9j)]=false;this[g0y]((L13+F43+z6i.u83+q0+z6i.w13));}
;Editor.prototype._closeReg=function(fn){var V7="loseCb";this[j03][(c9j+V7)]=fn;}
;Editor.prototype._crudArgs=function(arg1,arg2,arg3,arg4){var X5y="main",s5j='boo',O7j="isPlai",that=this,title,buttons,show,opts;if($[(O7j+z6i.W5j+H4R+u93+U5y)](arg1)){opts=arg1;}
else if(typeof arg1===(s5j+o4j+P73+t43)){show=arg1;opts=arg2;}
else{title=arg1;buttons=arg2;show=arg3;opts=arg4;}
if(show===undefined){show=true;}
if(title){that[(I1y+T5R)](title);}
if(buttons){that[y6](buttons);}
return {opts:$[n7R]({}
,this[j03][(z6i.X6j+i2j+E03+p5j+t6R+Q4j+z6i.W5j+j03)][(X5y)],opts),maybeOpen:function(){var w1R="open";if(show){that[w1R]();}
}
}
;}
;Editor.prototype._dataSource=function(name){var n5y="hift",args=Array.prototype.slice.call(arguments);args[(j03+n5y)]();var fn=this[j03][Q4][name];if(fn){return fn[b1j](this,args);}
}
;Editor.prototype._displayReorder=function(includeFields){var Q7y='Ord',x43='ma',D2="lat",D2j="emp",that=this,formContent=$(this[B0][(z6i.X6j+e63+I0y+z6i.w03+z6i.x6j+d43)]),fields=this[j03][i2y],order=this[j03][(S5+C1R+E03)],template=this[j03][(z6i.w03+D2j+D2+z6i.x6j)],mode=this[j03][g43]||(x43+j6);if(includeFields){this[j03][g93]=includeFields;}
else{includeFields=this[j03][(j6j+M9y+B33+z6i.V9j+z6i.x6j+Q1R+t8j+q5R)];}
formContent[Q3y]()[(z6i.V9j+z6i.x6j+D0y+c9j+c4j)]();$[(M8+c4j)](order,function(i,fieldOrName){var L6y="after",n1y="_weakInArray",name=fieldOrName instanceof Editor[(p1R+P4j+z6i.x6j+z6i.S8j+z6i.V9j)]?fieldOrName[(z6i.W5j+z6i.S1j+p5j+z6i.x6j)]():fieldOrName;if(that[n1y](name,includeFields)!==-1){if(template&&mode===(W43+P73+j6)){template[(z6i.X6j+P4j+x33)]((P9j+z6i.u83+V0+C7R+o93+d63+x03+n03+t43+l0y+z6i.w13+w2)+name+(X6y))[L6y](fields[name][(k93+C1R)]());template[a8R]('[data-editor-template="'+name+'"]')[o6y](fields[name][(z6i.W5j+o9+z6i.x6j)]());}
else{formContent[(m7j+B0y)](fields[name][(k93+z6i.V9j+z6i.x6j)]());}
}
}
);if(template&&mode===(x43+d63+t43)){template[R1R](formContent);}
this[(M7j+z6i.x6j+k33+z6i.x6j+z6i.W5j+z6i.w03)]((V13+d63+q0+T+v4y+Q7y+X2),[this[j03][(z6i.V9j+P4j+e6+z6i.S8j+i43+z6i.x6j+z6i.V9j)],this[j03][u6R],formContent]);}
;Editor.prototype._edit=function(items,editFields,type){var r6="_displayReorder",o4="plice",N2R="St",I1R="Array",o5y="tionC",F3="tFields",that=this,fields=this[j03][i2y],usedFields=[],includeInOrder,editData={}
;this[j03][(R93+F3)]=editFields;this[j03][(z6i.x6j+z6i.V9j+P4j+z6i.w03+l43+z6i.w03+z6i.S1j)]=editData;this[j03][(t7j+x6R+c0+T03)]=items;this[j03][(z6i.S1j+c9j+z6i.w03+P4j+i2j+z6i.W5j)]=(S3R);this[(z6i.V9j+u8)][(z6i.X6j+i2j+C33)][(j03+z6i.w03+z73+E5y)][(x6R+j03+h2j+z6i.S8j+z6i.S1j+z73)]=(z6i.w73+F43+J6R);this[j03][g43]=type;this[(q7y+o5y+z6i.S8j+S2y)]();$[(z6i.x6j+a6y)](fields,function(name,field){var t9R="iR";field[(p5j+B33+z6i.S8j+z6i.w03+t9R+z6i.x6j+j03+A33)]();includeInOrder=false;editData[name]={}
;$[(Y9j+b1y)](editFields,function(idSrc,edit){var T6R="iS",I9="omData";if(edit[i2y][name]){var val=field[(n1j+z6i.S8j+p1R+E03+I9)](edit.data);editData[name][idSrc]=val;if(!edit[(z6i.V9j+K6y+z6i.S8j+z6i.S1j+z73+Q1R+z6i.x6j+z6i.S8j+z6i.V9j+j03)]||edit[H0j][name]){field[(p5j+B33+K1R+T6R+z6i.x6j+z6i.w03)](idSrc,val!==undefined?val:field[(J5R)]());includeInOrder=true;}
}
}
);if(field[(y2R+P4j+v9R+z6i.V9j+j03)]().length!==0&&includeInOrder){usedFields[l6R](name);}
}
);var currOrder=this[z7j]()[V2]();for(var i=currOrder.length-1;i>=0;i--){if($[(P4j+z6i.W5j+I1R)](currOrder[i][(z6i.w03+i2j+N2R+E03+P4j+z6i.W5j+w6j)](),usedFields)===-1){currOrder[(j03+o4)](i,1);}
}
this[r6](currOrder);this[g0y]('initEdit',[_pluck(editFields,(s2R))[0],_pluck(editFields,'data')[0],items,type]);this[(M7j+H73+O5j+z6i.w03)]('initMultiEdit',[editFields,items,type]);}
;Editor.prototype._event=function(trigger,args){var h6j="result",B9R="Event";if(!args){args=[];}
if($[(j0y+E03+g73)](trigger)){for(var i=0,ien=trigger.length;i<ien;i++){this[g0y](trigger[i],args);}
}
else{var e=$[B9R](trigger);$(this)[K3j](e,args);return e[h6j];}
}
;Editor.prototype._eventName=function(input){var w5="substring",name,names=input[(j03+Z6R+z6i.w03)](' ');for(var i=0,ien=names.length;i<ien;i++){name=names[i];var onStyle=name[(p5j+X93+b1y)](/^on([A-Z])/);if(onStyle){name=onStyle[1][i9y]()+name[w5](3);}
names[i]=name;}
return names[(M4j+X5R)](' ');}
;Editor.prototype._fieldFromNode=function(node){var foundField=null;$[w4j](this[j03][i2y],function(name,field){if($(field[C0R]())[(z6i.X6j+P4j+x33)](node).length){foundField=field;}
}
);return foundField;}
;Editor.prototype._fieldNames=function(fieldNames){var E5j="isArr";if(fieldNames===undefined){return this[(i2y)]();}
else if(!$[(E5j+i43)](fieldNames)){return [fieldNames];}
return fieldNames;}
;Editor.prototype._focus=function(fieldsIn,focus){var u5j="setFocus",that=this,field,fields=$[(p5j+l73)](fieldsIn,function(fieldOrName){return typeof fieldOrName===(q0+J3+V0+N1j)?that[j03][(z6i.X6j+P7j+e13)][fieldOrName]:fieldOrName;}
);if(typeof focus==='number'){field=fields[focus];}
else if(focus){if(focus[L2y]('jq:')===0){field=$((V13+d63+R7+w7R+J3j+d8j+b3j+Q5y)+focus[(E03+v2j+z6i.S8j+X8j+z6i.x6j)](/^jq:/,''));}
else{field=this[j03][i2y][focus];}
}
this[j03][u5j]=field;if(field){field[g33]();}
}
;Editor.prototype._formOptions=function(opts){var K7y="tton",l63="utto",J4="utt",w1j="sage",o3j="essag",A13="mess",x3="tit",X3R="titl",q0R="editCount",y3j="blurOnBackground",s33="onBackground",I7j="groun",G9y="rOn",D9="submitOnReturn",l8="onReturn",R4R="Retu",W2R='clo',W73="lur",J43="OnC",K63="mpl",b03="Co",f0j="On",f3y='Inline',that=this,inlineCount=__inlineCounter++,namespace=(w7R+V13+w2R+f3y)+inlineCount;if(opts[(M9y+i2j+j03+z6i.x6j+f0j+b03+K63+z6i.x6j+h7y)]!==undefined){opts[N8R]=opts[(M9y+i2j+j03+z6i.x6j+J43+u8+h2j+z6i.S8j+r2R)]?(L13+F43+z6i.u83+q0+z6i.w13):'none';}
if(opts[(j03+B33+S9+G8j+f0j+q3R+y1R+E03)]!==undefined){opts[l8j]=opts[(x7j+p5j+G8j+f0j+q3R+W73)]?(q0+P3+z6i.w73+b7j):(W2R+q0+z6i.w13);}
if(opts[(g+P4j+z6i.w03+f0j+R4R+E03+z6i.W5j)]!==undefined){opts[l8]=opts[D9]?'submit':'none';}
if(opts[(i9j+z6i.S8j+B33+G9y+q3R+L4y+I7j+z6i.V9j)]!==undefined){opts[s33]=opts[y3j]?'blur':'none';}
this[j03][(z6i.x6j+H13+E3j+z6i.o8y)]=opts;this[j03][q0R]=inlineCount;if(typeof opts[(z6i.w03+G8j+E5y)]==='string'||typeof opts[Z4y]===(o93+P3+t43+L13+U3j+k9R)){this[(z6i.w03+P4j+T5R)](opts[(X3R+z6i.x6j)]);opts[(x3+E5y)]=true;}
if(typeof opts[X0j]===(Y93+j6+I93)||typeof opts[(A13+z6i.S1j+K0y)]==='function'){this[(p5j+o3j+z6i.x6j)](opts[(H2y+w1j)]);opts[X0j]=true;}
if(typeof opts[(i9j+J4+i2j+z6i.W5j+j03)]!=='boolean'){this[(i9j+l63+f63)](opts[(Y5+V2R+j03)]);opts[(i9j+B33+K7y+j03)]=true;}
$(document)[(i2j+z6i.W5j)]('keyup'+namespace,function(e){var P6R="next",t1y="eyC",O3y="onEsc",j0="sc",E2j='nction',h0j="Esc",q2R="Defa",z6R="prev",K9R='su',Y5R="ubm",P0j="rnS",f1j="nR",q7="canReturnSubmit",r9R="mNod",l0="_field",el=$(document[m7]);if(e[u43]===13&&that[j03][(z6i.V9j+K6y+V4y+z73+Z6j)]){var field=that[(l0+p1R+L73+r9R+z6i.x6j)](el);if(field&&typeof field[q7]==='function'&&field[(c9j+z6i.S1j+f1j+X1R+P0j+Y5R+G8j)](el)){if(opts[l8]===(K9R+z6i.w73+W43+d63+J3)){e[(z6R+P9+q2R+i0)]();that[(R8+S9+P4j+z6i.w03)]();}
else if(typeof opts[l8]==='function'){e[(N2y+z6i.x6j+K43+Z7R+S6j+z6i.S1j+i4R+z6i.w03)]();opts[l8](that);}
}
}
else if(e[(E8j+C13+A7R+w5R)]===27){e[(h2j+E03+z6i.x6j+k33+O5j+I0+S6j+z6i.S1j+B33+z6i.S8j+z6i.w03)]();if(typeof opts[(O8+h0j)]===(Z3R+E2j)){opts[(i2j+z6i.W5j+G7R+j0)](that);}
else if(opts[(i2j+z6i.W5j+G7R+j03+c9j)]===(Y3R+P3+V0)){that[(c9+E5R)]();}
else if(opts[O3y]==='close'){that[R0j]();}
else if(opts[O3y]===(q0+P3+z6i.w73+b7j)){that[(j03+B33+S9+G8j)]();}
}
else if(el[p6y]('.DTE_Form_Buttons').length){if(e[(E8j+t1y+i2j+z6i.V9j+z6i.x6j)]===37){el[z6R]((z6i.w73+p7R+k9R))[(c7+B0R)]();}
else if(e[(Z8+a4+z6i.x6j)]===39){el[P6R]((D7+t43))[g33]();}
}
}
);this[j03][(M9y+j4+w43)]=function(){$(document)[(v03)]((b9R+i1+I63)+namespace);}
;return namespace;}
;Editor.prototype._legacyAjax=function(direction,action,data){var t2R="acyAj",J4j="eg";if(!this[j03][(z6i.S8j+J4j+t2R+z6i.S1j+v73)]||!data){return ;}
if(direction==='send'){if(action==='create'||action==='edit'){var id;$[w4j](data.data,function(rowId,values){var e03='egacy',y63='orted';if(id!==undefined){throw (y5R+v8+z6i.u83+V0+i1R+N9j+P3+F43+J3+d63+C7R+V0+j8R+Q5y+z6i.w13+V13+v8+d63+E3y+Q5y+d63+q0+Q5y+t43+g4R+Q5y+q0+P3+T+T+y63+Q5y+z6i.w73+i1+Q5y+J3+r93+z6i.w13+Q5y+F43+e03+Q5y+J0j+z6i.b63+P9y+Q5y+V13+P73+t8R+Q5y+o93+z6i.u83+V0+U4R);}
id=rowId;}
);data.data=data.data[id];if(action===(z6i.w13+g13+J3)){data[(P4j+z6i.V9j)]=id;}
}
else{data[(J7j)]=$[x3R](data.data,function(values,id){return id;}
);delete  data.data;}
}
else{if(!data.data&&data[(L73+Y73)]){data.data=[data[T8]];}
else if(!data.data){data.data=[];}
}
}
;Editor.prototype._optionsUpdate=function(json){var O4j="optio",that=this;if(json[(O4j+z6i.W5j+j03)]){$[(Y9j+b1y)](this[j03][(c0+z6i.x6j+z6i.S8j+z6i.V9j+j03)],function(name,field){var m9j="update",G5j="upd",d1R="tions";if(json[(i2j+h2j+d1R)][name]!==undefined){var fieldInst=that[L3R](name);if(fieldInst&&fieldInst[(G5j+X93+z6i.x6j)]){fieldInst[m9j](json[(i2j+h2j+K3y+f63)][name]);}
}
}
);}
}
;Editor.prototype._message=function(el,msg){var B2y="isplay",T93='uncti';if(typeof msg===(o93+T93+z6i.u83+t43)){msg=msg(this,new DataTable[O2j](this[j03][(D0y+i9j+E5y)]));}
el=$(el);if(!msg&&this[j03][(x6R+j03+h2j+V4y+z73+Z6j)]){el[(j03+w6y+h2j)]()[(z6i.X6j+z6i.S1j+C1R+s4R+K2R)](function(){el[L5j]('');}
);}
else if(!msg){el[(Q4R+p5j+z6i.S8j)]('')[n43]((b0+q6j+P73+i1),'none');}
else if(this[j03][(z6i.V9j+B2y+Z6j)]){el[(j03+z6i.w03+i2j+h2j)]()[L5j](msg)[w3R]();}
else{el[(g7y+z6i.S8j)](msg)[n43]((b0+q6j+P73+i1),'block');}
}
;Editor.prototype._multiInfo=function(){var J83="Sho",a4y="iVal",a8y="Mul",L1="isM",O5="itabl",fields=this[j03][(z6i.X6j+s0+z6i.V9j+j03)],include=this[j03][g93],show=true,state;if(!include){return ;}
for(var i=0,ien=include.length;i<ien;i++){var field=fields[include[i]],multiEditable=field[(O6+z6i.w03+K1j+O5+z6i.x6j)]();if(field[(L1+B33+z6i.S8j+I1y+C4+r7R)]()&&multiEditable&&show){state=true;show=false;}
else if(field[(P4j+j03+a8y+z6i.w03+a4y+B33+z6i.x6j)]()&&!multiEditable){state=true;}
else{state=false;}
fields[include[i]][(y2R+P4j+J3y+c7+J83+Y73+z6i.W5j)](state);}
}
;Editor.prototype._postopen=function(type){var d03='rna',N8j='sub',that=this,focusCapture=this[j03][(z6i.V9j+P4j+j03+h2j+V4y+z73+A7R+i2j+z6i.W5j+l4y+C1y+z6i.x6j+E03)][(b3y+h2j+z6i.w03+B33+d5j+b6R+c9j+s5R)];if(focusCapture===undefined){focusCapture=true;}
$(this[(z6i.V9j+u8)][(R63)])[(v03)]((N8j+W43+v8+w7R+z6i.w13+V13+d63+n6j+C7R+d63+h6y+z6i.w13+d03+F43))[O8]((q0+P3+z6i.w73+W43+v8+w7R+z6i.w13+o8+V0+C7R+d63+t43+w2R+V0+t43+P73+F43),function(e){var T9y="preventDefault";e[T9y]();}
);if(focusCapture&&(type===(W43+P73+j6)||type==='bubble')){$((F7R+v3))[O8]((o93+w0R+P3+q0+w7R+z6i.w13+V13+d63+r1j+V0+C7R+o93+z6i.u83+L13+P3+q0),function(){var s5y="cu",N43="emen",V1R="eE",m3="tiv";if($(document[m7])[p6y]((w7R+J3j+f73)).length===0&&$(document[(z6i.S1j+c9j+m3+V1R+z6i.S8j+N43+z6i.w03)])[(h2j+q13+P9+j03)]((w7R+J3j+d8j+b3j+J3j)).length===0){if(that[j03][(s3+S3+i2j+c9j+B33+j03)]){that[j03][(j03+z6i.x6j+S3+i2j+c9j+B33+j03)][(c7+s5y+j03)]();}
}
}
);}
this[(c5y+B33+z6i.S8j+I1y+J3y+c7)]();this[(u6y+k33+O5j+z6i.w03)]((z6i.u83+T+H5),[type,this[j03][u6R]]);return true;}
;Editor.prototype._preopen=function(type){var Z43='inli',C1="ctio",W6j='O',U9="_eve";if(this[(U9+d43)]((T+r8+W6j+T+z6i.w13+t43),[type,this[j03][u6R]])===false){this[X4j]();this[g0y]('cancelOpen',[type,this[j03][(z6i.S1j+C1+z6i.W5j)]]);if((this[j03][(p5j+o9+z6i.x6j)]===(Z43+P0y)||this[j03][(p5j+i2j+z6i.V9j+z6i.x6j)]==='bubble')&&this[j03][K4]){this[j03][K4]();}
this[j03][K4]=null;return false;}
this[j03][(x6R+j03+S8y+i43+z6i.x6j+z6i.V9j)]=type;return true;}
;Editor.prototype._processing=function(processing){var Q4y='ssi',x63="toggleClass",G9="active",procClass=this[w0][L9j][G9];$(['div.DTE',this[B0][(U93+C0y)]])[x63](procClass,processing);this[j03][L9j]=processing;this[g0y]((b8j+z6i.u83+A0j+Q4y+t43+I93),[processing]);}
;Editor.prototype._submit=function(successCallback,errorCallback,formatdata,hide){var h03="_ajax",W9="Ur",r9j="_legacyAjax",L43='ete',C0j='tCo',Q7="lose",F7y='ang',C4j="dbT",a7y="dbTable",Z0="ssi",M73="_pro",i4y="ction",u0='Su',U4y='init',f6j="tData",v6R="dif",p83="tCou",r3y="SetO",that=this,i,iLen,eventRet,errorNodes,changed=false,allData={}
,changedData={}
,setBuilder=DataTable[(p13+z6i.w03)][(e5)][(M7j+z6i.X6j+z6i.W5j+r3y+i9j+M4j+z6i.x6j+c9j+z6i.w03+l43+r0R)],dataSource=this[j03][Q4],fields=this[j03][(z6i.X6j+P7j+z6i.S8j+q5R)],editCount=this[j03][(R93+p83+z6i.W5j+z6i.w03)],modifier=this[j03][(p5j+i2j+v6R+P4j+z6i.x6j+E03)],editFields=this[j03][h9j],editData=this[j03][(Z6j+P4j+f6j)],opts=this[j03][(S3R+t6R+j03)],changedSubmit=opts[(g+G8j)],submitParamsLocal;if(this[g0y]((U4y+u0+z6i.w73+b7j),[this[j03][(z6i.S1j+i4y)]])===false){this[(M73+c9j+z6i.x6j+Z0+h73)](false);return ;}
var action=this[j03][(X8j+I1y+i2j+z6i.W5j)],submitParams={"action":action,"data":{}
}
;if(this[j03][a7y]){submitParams[(z6i.w03+z6i.S1j+c9+z6i.x6j)]=this[j03][(C4j+G7y)];}
if(action===(o2R+X93+z6i.x6j)||action===(z6i.x6j+H13)){$[(z6i.x6j+a6y)](editFields,function(idSrc,edit){var R5="mpty",s6R="pty",q8j="sE",allRowData={}
,changedRowData={}
;$[(z6i.x6j+a6y)](fields,function(name,field){var m2j="are",C1j='[]',X2j="rom",E5="iGe";if(edit[i2y][name]){var multiGet=field[(y6j+K1R+E5+z6i.w03)](),builder=setBuilder(name);if(multiGet[idSrc]===undefined){var originalVal=field[(s73+p1R+X2j+l43+z6i.w03+z6i.S1j)](edit.data);builder(allRowData,originalVal);return ;}
var value=multiGet[idSrc],manyBuilder=$[p03](value)&&name[L2y]((C1j))!==-1?setBuilder(name[s9y](/\[.*$/,'')+'-many-count'):null;builder(allRowData,value);if(manyBuilder){manyBuilder(allRowData,value.length);}
if(action===(P9j)&&(!editData[name]||!field[(c9j+i2j+Z1j+m2j)](value,editData[name][idSrc]))){builder(changedRowData,value);changed=true;if(manyBuilder){manyBuilder(changedRowData,value.length);}
}
}
}
);if(!$[(P4j+q8j+p5j+s6R+H4R+u93+U5y)](allRowData)){allData[idSrc]=allRowData;}
if(!$[(P4j+j03+G7R+R5+H4R+M4j+z6i.x6j+U5y)](changedRowData)){changedData[idSrc]=changedRowData;}
}
);if(action===(L13+V0+z6i.w13+E73)||changedSubmit==='all'||(changedSubmit==='allIfChanged'&&changed)){submitParams.data=allData;}
else if(changedSubmit===(L13+r93+F7y+z6i.w13+V13)&&changed){submitParams.data=changedData;}
else{this[j03][u6R]=null;if(opts[N8R]===(L13+I2j+q0+z6i.w13)&&(hide===undefined||hide)){this[(M7j+c9j+Q7)](false);}
else if(typeof opts[(i2j+c5R+i2j+Z1j+z6i.S8j+r2R)]===(Z3R+t43+L13+J3+d63+k9R)){opts[N8R](this);}
if(successCallback){successCallback[q6R](this);}
this[R3j](false);this[(M7j+P33+d43)]((q0+H03+W43+d63+C0j+W43+T+F43+L43));return ;}
}
else if(action===(E03+z6i.x6j+p5j+i2j+I9j)){$[(z6i.x6j+a6y)](editFields,function(idSrc,edit){submitParams.data[idSrc]=edit.data;}
);}
this[r9j]((q0+H5+V13),action,submitParams);submitParamsLocal=$[n7R](true,{}
,submitParams);if(formatdata){formatdata(submitParams);}
if(this[(M7j+H73+z6i.x6j+z6i.W5j+z6i.w03)]('preSubmit',[submitParams,action])===false){this[R3j](false);return ;}
var submitWire=this[j03][(P03+z6i.S1j+v73)]||this[j03][(z6i.S1j+M4j+N63+W9+z6i.S8j)]?this[h03]:this[(M7j+V3y+j5R+z6i.S1j+c9+z6i.x6j)];submitWire[q6R](this,submitParams,function(json,notGood,xhr){var f2R="cces";that[(M7j+j03+B33+S9+P4j+z6i.w03+p5R+B33+f2R+j03)](json,notGood,submitParams,submitParamsLocal,that[j03][(l3j+L2R)],editCount,hide,successCallback,errorCallback,xhr);}
,function(xhr,err,thrown){var E3="tE",g6="_subm";that[(g6+P4j+E3+E03+E03+i2j+E03)](xhr,err,thrown,errorCallback,submitParams,that[j03][u6R]);}
,submitParams);}
;Editor.prototype._submitTable=function(data,success,error,submitParams){var J8="ifie",Y8y='fi',u1j="our",R6j="_fnSetObjectDataFn",I0R="tDa",W3R="jec",a8j="tOb",l9R="_fn",that=this,action=data[(X8j+z6i.w03+Q4j+z6i.W5j)],out={data:[]}
,idGet=DataTable[r7j][(i2j+C3R+g4y)][(l9R+l1R+z6i.x6j+a8j+W3R+I0R+z6i.w03+z6i.S1j+i6R)](this[j03][(J7j+p5R+n8j)]),idSet=DataTable[(p13+z6i.w03)][e5][R6j](this[j03][J5y]);if(action!==(z5j+z6i.u83+R7+z6i.w13)){var originalData=this[(q2+z6i.w03+z6i.S1j+p5R+u1j+c9j+z6i.x6j)]((Y8y+z6i.w13+G6j+q0),this[(t7j+z6i.V9j+J8+E03)]());$[(z6i.x6j+z6i.S1j+c9j+c4j)](data.data,function(key,vals){var toSave;if(action==='edit'){var rowData=originalData[key].data;toSave=$[n7R](true,{}
,rowData,vals);}
else{toSave=$[n7R](true,{}
,vals);}
if(action==='create'&&idGet(toSave)===undefined){idSet(toSave,+new Date()+''+key);}
else{idSet(toSave,key);}
out.data[(h2j+W6R)](toSave);}
);}
success(out);}
;Editor.prototype._submitSuccess=function(json,notGood,submitParams,submitParamsLocal,action,editCount,hide,successCallback,errorCallback,xhr){var l3y='let',Y4y='Com',L9y='bmi',G0='Suc',w8R='ubmi',h13="plet",o43="onCo",m5="os",d1="tCo",P3j="Sou",v4='stRem',n5R="So",T4R='preRe',B8R="ven",W4="taS",p1y='pre',e0y='Cr',k4j='po',q3j="aS",I6="_dat",e1y="ldE",v0R="dEr",i9='Submi',V8="yA",t0j="egac",x6="modif",t63="Opts",that=this,setData,fields=this[j03][(R9+z6i.S8j+q5R)],opts=this[j03][(Z6j+G8j+t63)],modifier=this[j03][(x6+P4j+T03)];this[(G8y+t0j+V8+R1j)]('receive',action,json);this[(u6y+K43)]((s5+i9+J3),[json,submitParams,action,xhr]);if(!json.error){json.error="";}
if(!json[X7R]){json[(z6i.X6j+s0+v0R+E03+S5+j03)]=[];}
if(notGood||json.error||json[(z6i.X6j+P4j+z6i.x6j+e1y+W33+j03)].length){this.error(json.error);$[w4j](json[(L3R+n6y+L73+c13)],function(i,err){var J2j="eldE",X2R="nF",P7="onFieldError",field=fields[err[(E4j)]];field.error(err[F93]||"Error");if(i===0){if(opts[P7]===(o93+z6i.u83+L13+e43)){$(that[(z6i.V9j+i2j+p5j)][N6],that[j03][(Y73+E03+z6i.S1j+c2y+z6i.x6j+E03)])[(a73+P4j+r8R+z6i.w03+z6i.x6j)]({"scrollTop":$(field[(z6i.W5j+o9+z6i.x6j)]()).position().top}
,500);field[g33]();}
else if(typeof opts[(i2j+X2R+s0+z6i.V9j+G7R+E03+L73+E03)]==='function'){opts[(i2j+z6i.W5j+p1R+P4j+J2j+E03+E03+i2j+E03)](that,err);}
}
}
);this[(M7j+z6i.x6j+K43)]('submitUnsuccessful',[json]);if(errorCallback){errorCallback[(b3y+e0R)](that,json);}
}
else{var store={}
;if(json.data&&(action===(m4y+Y9j+h7y)||action===(z6i.x6j+z6i.V9j+P4j+z6i.w03))){this[(r9y+z6i.S1j+z6i.w03+z6i.S1j+p5R+i2j+E5R+X7y)]((b8j+z6i.w13+T),action,modifier,submitParamsLocal,json,store);for(var i=0;i<json.data.length;i++){setData=json.data[i];this[g0y]('setData',[json,setData,action]);if(action===(c9j+d5j+z6i.S1j+h7y)){this[g0y]('preCreate',[json,setData]);this[(I6+q3j+j2+n8j+z6i.x6j)]('create',fields,setData,store);this[(M7j+z6i.x6j+k33+z6i.x6j+d43)]([(L13+M6j),(k4j+q0+J3+e0y+z6i.w13+P73+J3+z6i.w13)],[json,setData]);}
else if(action===(z6i.x6j+z6i.V9j+P4j+z6i.w03)){this[g0y]((p1y+b3j+V13+d63+J3),[json,setData]);this[a4j]((w+J3),modifier,fields,setData,store);this[g0y]([(z6i.w13+L0),'postEdit'],[json,setData]);}
}
this[(M7j+z6i.V9j+z6i.S1j+W4+j2+E2)]((L13+H9R+W43+v8),action,modifier,json.data,store);}
else if(action===(E03+z6i.x6j+p5j+q8R)){this[a4j]('prep',action,modifier,submitParamsLocal,json,store);this[(M7j+z6i.x6j+B8R+z6i.w03)]((T4R+W43+z6i.u83+j9),[json]);this[(q2+z6i.w03+z6i.S1j+n5R+E5R+c9j+z6i.x6j)]((V0+z6i.w13+W43+z6i.u83+R7+z6i.w13),modifier,fields,store);this[(M7j+z6i.x6j+k33+P9)]([(d0j),(k4j+v4+z6i.u83+R7+z6i.w13)],[json]);this[(r9y+z6i.S1j+z6i.w03+z6i.S1j+P3j+E03+X7y)]((L13+H9R+b7j),action,modifier,json.data,store);}
if(editCount===this[j03][(Z6j+P4j+d1+B33+z6i.W5j+z6i.w03)]){this[j03][u6R]=null;if(opts[N8R]===(q7j+z6i.u83+q0+z6i.w13)&&(hide===undefined||hide)){this[(M7j+c9j+z6i.S8j+m5+z6i.x6j)](json.data?true:false);}
else if(typeof opts[(o43+Z1j+z6i.S8j+z6i.x6j+z6i.w03+z6i.x6j)]==='function'){opts[(O8+A7R+u8+h13+z6i.x6j)](this);}
}
if(successCallback){successCallback[q6R](that,json);}
this[(M7j+P33+d43)]((q0+w8R+J3+G0+L13+l2+q0),[json,setData,action]);}
this[R3j](false);this[g0y]((q0+P3+L9y+J3+Y4y+T+l3y+z6i.w13),[json,setData,action]);}
;Editor.prototype._submitError=function(xhr,err,thrown,errorCallback,submitParams,action){var Y3='tCom',j8='subm',q2j='tError',u03="_even",X5="sy";this[g0y]('postSubmit',[null,submitParams,action,xhr]);this.error(this[U7].error[(X5+j03+z6i.w03+z6i.x6j+p5j)]);this[R3j](false);if(errorCallback){errorCallback[q6R](this,xhr,err,thrown);}
this[(u03+z6i.w03)]([(H63+q2j),(j8+d63+Y3+T+F43+z6i.w13+J3+z6i.w13)],[xhr,err,thrown,submitParams]);}
;Editor.prototype._tidy=function(fn){var W03='ubb',o7="play",q63="one",o3='mpl',V3j="atu",K7R="Fe",that=this,dt=this[j03][(D0y+c9+z6i.x6j)]?new $[(Y7)][(z6i.V9j+X93+z6i.S1j+p7y+E5y)][O2j](this[j03][(z6i.w03+z6i.S1j+c9+z6i.x6j)]):null,ssp=false;if(dt){ssp=dt[F5]()[0][(i2j+K7R+V3j+E03+z6i.x6j+j03)][m0R];}
if(this[j03][(N+c9j+z3y+P4j+z6i.W5j+w6j)]){this[(i2j+X33)]((H63+J3+g2+o3+z6i.w13+w2R),function(){var Y9y='aw';if(ssp){dt[q63]((V13+V0+Y9y),fn);}
else{setTimeout(function(){fn();}
,10);}
}
);return true;}
else if(this[(M43)]()===(d63+r7y+w0j)||this[(z6i.V9j+P4j+j03+o7)]()===(z6i.w73+W03+F43+z6i.w13)){this[(q63)]((L13+F43+z6i.u83+q0+z6i.w13),function(){var D9y='Comp';if(!that[j03][L9j]){setTimeout(function(){fn();}
,10);}
else{that[q63]((q0+H03+b7j+D9y+o4j+J3+z6i.w13),function(e,json){if(ssp&&json){dt[q63]('draw',fn);}
else{setTimeout(function(){fn();}
,10);}
}
);}
}
)[x73]();return true;}
return false;}
;Editor.prototype._weakInArray=function(name,arr){for(var i=0,ien=arr.length;i<ien;i++){if(name==arr[i]){return i;}
}
return -1;}
;Editor[(C1R+g63+i0+j03)]={"table":null,"ajaxUrl":null,"fields":[],"display":(Q6+r93+J3+z6i.w73+z6i.u83+X7),"ajax":null,"idSrc":(J3j+d8j+C4R+z6i.u83+b4R),"events":{}
,"i18n":{"create":{"button":(c4y+Y73),"title":(A7R+P+z6i.x6j+M2+z6i.W5j+z6i.x6j+Y73+M2+z6i.x6j+z6i.W5j+z2y),"submit":"Create"}
,"edit":{"button":"Edit","title":"Edit entry","submit":"Update"}
,"remove":{"button":(Z7R+r1R+z6i.w03+z6i.x6j),"title":(Z7R+z6i.x6j+z6i.S8j+r2R),"submit":(Z7R+z6i.x6j+z6i.S8j+r2R),"confirm":{"_":(C3R+d5j+M2+z73+i2j+B33+M2+j03+B33+d5j+M2+z73+j2+M2+Y73+C8j+c4j+M2+z6i.w03+i2j+M2+z6i.V9j+z6i.x6j+E5y+z6i.w03+z6i.x6j+B1+z6i.V9j+M2+E03+i2j+D1+i3R),"1":(I4+M2+z73+j2+M2+j03+B33+E03+z6i.x6j+M2+z73+i2j+B33+M2+Y73+C8j+c4j+M2+z6i.w03+i2j+M2+z6i.V9j+H+M2+M6y+M2+E03+i2j+Y73+i3R)}
}
,"error":{"system":(C3R+M2+j03+B83+z6i.x6j+p5j+M2+z6i.x6j+E03+E03+i2j+E03+M2+c4j+J93+M2+i2j+y0y+J2y+J8R+z6i.S1j+M2+z6i.w03+C03+z6i.x6j+z6i.w03+j5y+M7j+c9+z6i.S1j+D13+X2y+c4j+G3j+r5R+z6i.V9j+z6i.S1j+z6i.w03+X43+z6i.S8j+l03+b9y+z6i.W5j+A33+Q6y+z6i.w03+z6i.W5j+Q6y+M6y+d4y+L0j+m6R+S5+z6i.x6j+M2+P4j+z6i.W5j+z6i.X6j+i2j+E03+p5j+k9y+O8+n9j+z6i.S1j+z6j)}
,multi:{title:(m6R+B33+z6i.S8j+I1y+t1R+M2+k33+Y33+r7R+j03),info:(v5+M2+j03+z6i.x6j+s3j+Z6j+M2+P4j+M8j+M2+c9j+t2j+z6i.S1j+P4j+z6i.W5j+M2+z6i.V9j+S0y+z6i.W5j+z6i.w03+M2+k33+z6i.S1j+W7R+M2+z6i.X6j+i2j+E03+M2+z6i.w03+h83+M2+P4j+Q63+B33+z6i.w03+I9y+j5R+i2j+M2+z6i.x6j+x6R+z6i.w03+M2+z6i.S1j+x33+M2+j03+z6i.x6j+z6i.w03+M2+z6i.S1j+z6i.S8j+z6i.S8j+M2+P4j+z6i.w03+z6i.x6j+C9j+M2+z6i.X6j+S5+M2+z6i.w03+h83+M2+P4j+Q63+B33+z6i.w03+M2+z6i.w03+i2j+M2+z6i.w03+K3R+M2+j03+z6i.S1j+z6i.b2R+M2+k33+L0R+Q33+c9j+z6i.S8j+P4j+B9y+M2+i2j+E03+M2+z6i.w03+l73+M2+c4j+a5+Q33+i2j+z6i.w03+h8j+Y73+C8j+z6i.x6j+M2+z6i.w03+c4j+C13+M2+Y73+P4j+z6i.S8j+z6i.S8j+M2+E03+D3+z6i.W5j+M2+z6i.w03+Y5j+M2+P4j+z6i.W5j+z6i.V9j+P4j+o6+z6i.S8j+M2+k33+Y33+B33+l03+b9y),restore:(K1+z6i.V9j+i2j+M2+c9j+f2y+z6i.W5j+w6j+l03),noMulti:(j5R+m3R+j03+M2+P4j+F2j+M2+c9j+a73+M2+i9j+z6i.x6j+M2+z6i.x6j+z6i.V9j+g1j+M2+P4j+x33+S5j+J7j+B33+z6i.S1j+Q8R+Q33+i9j+B33+z6i.w03+M2+z6i.W5j+i2j+z6i.w03+M2+h2j+q13+z6i.w03+M2+i2j+z6i.X6j+M2+z6i.S1j+M2+w6j+E03+i2j+B33+h2j+b9y)}
,"datetime":{previous:(r6j+V0+c3y+d63+z6i.u83+e43),next:'Next',months:[(R3y+P3+P73+V0+i1),(w3j+z6i.w13+z6i.w73+B1R+V0+i1),'March',(g6j+V0+d63+F43),(A3R+i1),'June','July','August',(J13+T+J3+z6i.w13+W43+u1R),'October','November',(Q5+V0)],weekdays:['Sun','Mon',(d8j+P3+z6i.w13),(P5j+z6i.w13+V13),(d8j+r93+P3),'Fri',(G4j+B1y)],amPm:[(l0y),(Y4j)],unknown:'-'}
}
,formOptions:{bubble:$[n7R]({}
,Editor[(p5j+o9+M33)][j7],{title:false,message:false,buttons:'_basic',submit:'changed'}
),inline:$[n7R]({}
,Editor[Z03][(y93+O63+j03)],{buttons:false,submit:(L13+H5y+b6j)}
),main:$[(p13+h7y+z6i.W5j+z6i.V9j)]({}
,Editor[(t7j+C1R+z6i.S8j+j03)][(c7+v8y+h2j+z6i.w03+P4j+p2j)])}
,legacyAjax:false}
;(function(){var o8R="rowIds",w3="any",x1y="ields",q0j="_fnGetObjectDataFn",i7="cells",O43="index",X7j="mn",g0j='ind',__dataSources=Editor[n2y]={}
,__dtIsSsp=function(dt,editor){var b2="wTy";var J33="oFeatures";return dt[F5]()[0][J33][m0R]&&editor[j03][G1j][(z6i.V9j+Z4j+b2+h2j+z6i.x6j)]!==(t43+z6i.u83+t43+z6i.w13);}
,__dtApi=function(table){var L6="ataT";return $(table)[(Z7R+L6+z6i.S1j+i9j+E5y)]();}
,__dtHighlight=function(node){node=$(node);setTimeout(function(){node[(B73+z6i.S8j+S2y)]('highlight');setTimeout(function(){var e1='ighl';var y6R='ghl';var l5y='oHi';node[(z6i.S1j+z6i.V9j+z6i.V9j+A7R+R6y)]((t43+l5y+y6R+d63+J4R))[l0j]((r93+e1+n1+j93));setTimeout(function(){var w93='ighligh';var d3y='oH';node[(i6j+i2j+I9j+o2j+J93+j03)]((t43+d3y+w93+J3));}
,550);}
,500);}
,20);}
,__dtRowSelector=function(out,dt,identifier,fields,idFn){var Y2="xe";dt[H93](identifier)[(P4j+x33+z6i.x6j+Y2+j03)]()[w4j](function(idx){var g5R='fier';var h2='denti';var row=dt[(E03+u0y)](idx);var data=row.data();var idSrc=idFn(data);if(idSrc===undefined){Editor.error((D8j+t43+P73+z6i.w73+F43+z6i.w13+Q5y+J3+z6i.u83+Q5y+o93+g0j+Q5y+V0+j8R+Q5y+d63+h2+g5R),14);}
out[idSrc]={idSrc:idSrc,data:data,node:row[C0R](),fields:fields,type:'row'}
;}
);}
,__dtFieldsFromIdx=function(dt,fields,idx){var U2R='pecif';var S7R="tyO";var G43="tFi";var field;var col=dt[(j03+z6i.x6j+j8y+P4j+h73+j03)]()[0][(z6i.S1j+i2j+A7R+i2j+y1R+X7j+j03)][idx];var dataSrc=col[(z6i.x6j+x6R+G43+z6i.x6j+z6i.S8j+z6i.V9j)]!==undefined?col[(z6i.x6j+z6i.V9j+G8j+p1R+s0+z6i.V9j)]:col[(p5j+l43+D0y)];var resolvedFields={}
;var run=function(field,dataSrc){if(field[E4j]()===dataSrc){resolvedFields[field[E4j]()]=field;}
}
;$[(z6i.x6j+X8j+c4j)](fields,function(name,fieldInst){if($[(C8j+C3R+B13+z6i.S1j+z73)](dataSrc)){for(var i=0;i<dataSrc.length;i++){run(fieldInst,dataSrc[i]);}
}
else{run(fieldInst,dataSrc);}
}
);if($[(P4j+j03+G7R+Z1j+S7R+i9j+u93+U5y)](resolvedFields)){Editor.error((Q0R+N73+Q5y+J3+z6i.u83+Q5y+P73+P3+r1j+U4R+d63+L13+P73+m5j+i1+Q5y+V13+d0y+z6i.w13+T0y+j6+z6i.w13+Q5y+o93+d63+I8+V13+Q5y+o93+V0+H9R+Q5y+q0+z6i.u83+h43+L13+z6i.w13+S7j+r6j+E9+V5y+Q5y+q0+U2R+i1+Q5y+J3+r93+z6i.w13+Q5y+o93+d63+x03+Q5y+t43+l0y+z6i.w13+w7R),11);}
return resolvedFields;}
,__dtCellSelector=function(out,dt,identifier,allFields,idFn,forceFields){dt[(c9j+N4R)](identifier)[(O43+z6i.x6j+j03)]()[(z6i.x6j+a6y)](function(idx){var R5y="ttach";var C2="tach";var p6="ispla";var M0="tac";var G63="Nam";var X0R="umn";var s43="col";var k3R="cell";var cell=dt[k3R](idx);var row=dt[T8](idx[T8]);var data=row.data();var idSrc=idFn(data);var fields=forceFields||__dtFieldsFromIdx(dt,allFields,idx[(s43+X0R)]);var isNode=(typeof identifier==='object'&&identifier[(z6i.W5j+w5R+G63+z6i.x6j)])||identifier instanceof $;var prevDisplayFields,prevAttach;if(out[idSrc]){prevAttach=out[idSrc][(X93+M0+c4j)];prevDisplayFields=out[idSrc][(z6i.V9j+p6+z73+p1R+P7j+e13)];}
__dtRowSelector(out,dt,idx[T8],allFields,idFn);out[idSrc][(X93+C2)]=prevAttach||[];out[idSrc][(z6i.S1j+R5y)][l6R](isNode?$(identifier)[(V9R)](0):cell[(z6i.W5j+i2j+z6i.V9j+z6i.x6j)]());out[idSrc][(x6R+e6+V4y+z73+p1R+P4j+z6i.x6j+O8y+j03)]=prevDisplayFields||{}
;$[n7R](out[idSrc][H0j],fields);}
);}
,__dtColumnSelector=function(out,dt,identifier,fields,idFn){dt[i7](null,identifier)[a8]()[w4j](function(idx){__dtCellSelector(out,dt,idx,fields,idFn);}
);}
,__dtjqId=function(id){var x9y="ace";return typeof id===(Y93+d63+t43+I93)?'#'+id[(d5j+S8y+x9y)](/(:|\.|\[|\]|,)/g,'\\$1'):'#'+id;}
;__dataSources[(z6i.V9j+X93+c7j+z6i.F8j+E5y)]={individual:function(identifier,fieldNames){var A="Src",idFn=DataTable[r7j][e5][q0j](this[j03][(J7j+A)]),dt=__dtApi(this[j03][(z6i.w03+z6i.S1j+c9+z6i.x6j)]),fields=this[j03][i2y],out={}
,forceFields,responsiveNode;if(fieldNames){if(!$[p03](fieldNames)){fieldNames=[fieldNames];}
forceFields={}
;$[(Y9j+c9j+c4j)](fieldNames,function(i,name){forceFields[name]=fields[name];}
);}
__dtCellSelector(out,dt,identifier,fields,idFn,forceFields);return out;}
,fields:function(identifier){var T2R="cel",J2R="olu",n0="ObjectD",idFn=DataTable[(z6i.x6j+C9y)][(i2j+C3R+h2j+P4j)][(M7j+z6i.X6j+z6i.W5j+l1R+A33+n0+X93+z6i.S1j+p1R+z6i.W5j)](this[j03][J5y]),dt=__dtApi(this[j03][(z6i.w03+z6i.F8j+E5y)]),fields=this[j03][(z6i.X6j+x1y)],out={}
;if($[m1R](identifier)&&(identifier[(E03+u0y+j03)]!==undefined||identifier[P5R]!==undefined||identifier[i7]!==undefined)){if(identifier[(L73+Y73+j03)]!==undefined){__dtRowSelector(out,dt,identifier[H93],fields,idFn);}
if(identifier[(c9j+J2R+X7j+j03)]!==undefined){__dtColumnSelector(out,dt,identifier[(c9j+x8+B33+X7j+j03)],fields,idFn);}
if(identifier[(T2R+I7R)]!==undefined){__dtCellSelector(out,dt,identifier[i7],fields,idFn);}
}
else{__dtRowSelector(out,dt,identifier,fields,idFn);}
return out;}
,create:function(fields,data){var dt=__dtApi(this[j03][l13]);if(!__dtIsSsp(dt,this)){var row=dt[T8][(z6i.S1j+P1R)](data);__dtHighlight(row[(z6i.W5j+i2j+C1R)]());}
}
,edit:function(identifier,fields,data,store){var D3j="ic",V4R="rray",n5j="taF",Z3="fnG",s03="wT",dt=__dtApi(this[j03][(z6i.w03+z6i.S1j+i9j+E5y)]);if(!__dtIsSsp(dt,this)||this[j03][(z6i.x6j+H13+s4R+h2j+z6i.o8y)][(z6i.V9j+Z4j+s03+z73+Y6y)]===(W1y+t43+z6i.w13)){var idFn=DataTable[(p13+z6i.w03)][e5][(M7j+Z3+z6i.x6j+z6i.w03+H4R+M4j+M1R+l43+n5j+z6i.W5j)](this[j03][J5y]),rowId=idFn(data),row;try{row=dt[(L73+Y73)](__dtjqId(rowId));}
catch(e){row=dt;}
if(!row[(a73+z73)]()){row=dt[T8](function(rowIdx,rowData,rowNode){return rowId==idFn(rowData);}
);}
if(row[w3]()){row.data(data);var idx=$[(P4j+W8R+V4R)](rowId,store[o8R]);store[(T8+v9R+z6i.V9j+j03)][(e6+z6i.S8j+D3j+z6i.x6j)](idx,1);}
else{row=dt[(E03+i2j+Y73)][(z6i.S1j+P1R)](data);}
__dtHighlight(row[C0R]());}
}
,remove:function(identifier,fields,store){var T5y="every",i8y="dS",b2j="oA",a9R="cancelled",dt=__dtApi(this[j03][l13]),cancelled=store[a9R];if(cancelled.length===0){dt[H93](identifier)[F1]();}
else{var idFn=DataTable[r7j][(b2j+g4y)][q0j](this[j03][(P4j+i8y+n8j)]),indexes=[];dt[H93](identifier)[T5y](function(){var g5j="inA",id=idFn(this.data());if($[(g5j+E03+E03+z6i.S1j+z73)](id,cancelled)===-1){indexes[l6R](this[(O43)]());}
}
);dt[(E03+u0y+j03)](indexes)[F1]();}
}
,prep:function(action,identifier,submit,json,store){var E4R="ell",u5R="cance";if(action==='edit'){var cancelled=json[(u5R+z6i.S8j+z6i.S8j+z6i.x6j+z6i.V9j)]||[];store[o8R]=$[x3R](submit.data,function(val,key){var Y8j="isEmptyObject";return !$[Y8j](submit.data[key])&&$[y4j](key,cancelled)===-1?key:undefined;}
);}
else if(action===(V0+z6i.w13+W43+L2)){store[(b3y+k03+E4R+Z6j)]=json[(c9j+z6i.S1j+z6i.W5j+X7y+e0R+Z6j)]||[];}
}
,commit:function(action,identifier,data,store){var j1='one',Y0="Typ",y3y="ditO",u4j="idSr",E0R="ataFn",w7="tObj",r6R="rowI",dt=__dtApi(this[j03][(D0y+E63)]);if(action===(u6+v8)&&store[(r6R+z6i.V9j+j03)].length){var ids=store[(r6R+q5R)],idFn=DataTable[(z6i.x6j+C9y)][e5][(k6y+z6i.W5j+l1R+z6i.x6j+w7+G9j+z6i.w03+Z7R+E0R)](this[j03][(u4j+c9j)]),row,compare=function(id){return function(rowIdx,rowData,rowNode){return id==idFn(rowData);}
;}
;for(var i=0,ien=ids.length;i<ien;i++){try{row=dt[(T8)](__dtjqId(ids[i]));}
catch(e){row=dt;}
if(!row[(a73+z73)]()){row=dt[(T8)](compare(ids[i]));}
if(row[w3]()){row[F1]();}
}
}
var drawType=this[j03][(z6i.x6j+y3y+h2j+z6i.w03+j03)][(z6i.V9j+Z4j+Y73+Y0+z6i.x6j)];if(drawType!==(t43+j1)){dt[(z6i.V9j+Z4j+Y73)](drawType);}
}
}
;function __html_el(identifier,name){var O2y='` ',m73=' `',F03='ith',g9R='eyles',context=document;if(identifier!==(D63+g9R+q0)){context=$((n03+V13+P73+J3+P73+C7R+z6i.w13+o8+V0+C7R+d63+V13+w2)+identifier+'"]');if(context.length===0){throw (D0j+z6i.u83+b93+V13+Q5y+t43+g4R+Q5y+o93+g0j+Q5y+P73+t43+Q5y+z6i.w13+o4j+W43+H5+J3+Q5y+n7+F03+m73+V13+j73+C7R+z6i.w13+V13+u5+V0+C7R+d63+V13+O2y+z6i.u83+o93+i1R)+identifier;}
}
return $((n03+V13+P73+J3+P73+C7R+z6i.w13+L0+z6i.u83+V0+C7R+o93+d63+z6i.w13+G6j+w2)+name+(X6y),context);}
function __html_els(identifier,names){var out=$();for(var i=0,ien=names.length;i<ien;i++){out=out[p6R](__html_el(identifier,names[i]));}
return out;}
function __html_get(identifier,dataSrc){var C9="filter",el=__html_el(identifier,dataSrc);return el[C9]((n03+V13+P73+J3+P73+C7R+z6i.w13+o8+V0+C7R+R7+b9j+m03)).length?el[(z6i.S1j+j8y+E03)]((V13+j73+C7R+z6i.w13+q5j+C7R+R7+P73+F43+P3+z6i.w13)):el[(c4j+z6i.w03+a7j)]();}
function __html_set(identifier,fields,data){$[w4j](fields,function(name,field){var u="dataSrc",T1j="mData",val=field[(n1j+z6i.S8j+p1R+L73+T1j)](data);if(val!==undefined){var el=__html_el(identifier,field[u]());if(el[(z6i.X6j+O9j+h7y+E03)]((n03+V13+j73+C7R+z6i.w13+L0+w6R+C7R+R7+P73+S6+m03)).length){el[G2y]((V13+j73+C7R+z6i.w13+g13+J3+z6i.u83+V0+C7R+R7+P73+S6),val);}
else{el[w4j](function(){var i3y="firstChild",E0y="removeChild",A8y="childNodes";while(this[A8y].length){this[E0y](this[i3y]);}
}
)[(Q4R+p5j+z6i.S8j)](val);}
}
}
);}
__dataSources[(c4j+A6y+z6i.S8j)]={initField:function(cfg){var label=$('[data-editor-label="'+(cfg.data||cfg[(r2j+z6i.b2R)])+'"]');if(!cfg[(V4y+f3+z6i.S8j)]&&label.length){cfg[H2R]=label[L5j]();}
}
,individual:function(identifier,fieldNames){var E9y='erm',R2R='ca',S4y='not',h6='Ca',Z7y='ey',j1R="Ba",attachEl;if(identifier instanceof $||identifier[c8j]){attachEl=identifier;if(!fieldNames){fieldNames=[$(identifier)[(X93+l4y)]('data-editor-field')];}
var back=$[Y7][(p6R+j1R+B9y)]?'addBack':(a3y+V13+G4j+I8+o93);identifier=$(identifier)[p6y]((n03+V13+j73+C7R+z6i.w13+L0+w6R+C7R+d63+V13+m03))[back]().data('editor-id');}
if(!identifier){identifier=(D63+Z7y+F43+z6i.w13+s1R);}
if(fieldNames&&!$[(C8j+C3R+E03+g73)](fieldNames)){fieldNames=[fieldNames];}
if(!fieldNames||fieldNames.length===0){throw (h6+t43+S4y+Q5y+P73+P3+r1j+U4R+d63+R2R+m5j+i1+Q5y+V13+d0y+E9y+w0j+Q5y+o93+W7+G6j+Q5y+t43+P73+W43+z6i.w13+Q5y+o93+o3y+W43+Q5y+V13+P73+J3+P73+Q5y+q0+C2j+L13+z6i.w13);}
var out=__dataSources[(Q4R+a7j)][i2y][(c9j+z6i.S1j+z6i.S8j+z6i.S8j)](this,identifier),fields=this[j03][i2y],forceFields={}
;$[(w4j)](fieldNames,function(i,name){forceFields[name]=fields[name];}
);$[(w4j)](out,function(id,set){var Q1="toArray";set[d33]=(A0j+m5j);set[A0y]=attachEl?$(attachEl):__html_els(identifier,fieldNames)[Q1]();set[(z6i.X6j+x1y)]=fields;set[H0j]=forceFields;}
);return out;}
,fields:function(identifier){var z4="tml",out={}
,self=__dataSources[(c4j+z4)];if($[p03](identifier)){for(var i=0,ien=identifier.length;i<ien;i++){var res=self[i2y][q6R](this,identifier[i]);out[identifier[i]]=res[identifier[i]];}
return out;}
var data={}
,fields=this[j03][(z6i.X6j+P7j+z6i.S8j+q5R)];if(!identifier){identifier='keyless';}
$[w4j](fields,function(name,field){var x2j="valToData",val=__html_get(identifier,field[(z6i.V9j+z6i.S1j+D0y+p5R+E03+c9j)]());field[x2j](data,val===null?undefined:val);}
);out[identifier]={idSrc:identifier,data:data,node:document,fields:fields,type:(V0+j8R)}
;return out;}
,create:function(fields,data){var s0y="jectD",A1y="nGe";if(data){var idFn=DataTable[r7j][(e5)][(k6y+A1y+z6i.w03+H4R+s0y+z6i.S1j+r0R)](this[j03][(P4j+z6i.V9j+p5R+E03+c9j)]),id=idFn(data);if($((n03+V13+B1y+P73+C7R+z6i.w13+V13+d63+J3+z6i.u83+V0+C7R+d63+V13+w2)+id+(X6y)).length){__html_set(id,fields,data);}
}
}
,edit:function(identifier,fields,data){var M2R="nG",idFn=DataTable[r7j][e5][(k6y+M2R+A33+H4R+u93+U5y+Z7R+c7y+p1R+z6i.W5j)](this[j03][J5y]),id=idFn(data)||'keyless';__html_set(id,fields,data);}
,remove:function(identifier,fields){$((n03+V13+P73+t8R+C7R+z6i.w13+L0+z6i.u83+V0+C7R+d63+V13+w2)+identifier+(X6y))[(A8j+k33+z6i.x6j)]();}
}
;}
());Editor[(I5+j03+s3+j03)]={"wrapper":"DTE","processing":{"indicator":(Z7R+j5R+G7R+M7j+R8R+V9+j03+j03+j6j+w6j+M7j+v9R+e8R+E2R+E03),"active":(N2y+i2j+Q9R+h73)}
,"header":{"wrapper":(Z7R+c93+Y9R+f6R+E03),"content":"DTE_Header_Content"}
,"body":{"wrapper":(Z7R+j5R+G7R+J1+i2j+u3j),"content":"DTE_Body_Content"}
,"footer":{"wrapper":"DTE_Footer","content":(Z7R+c93+b6R+i2j+h7y+P6j+A7R+O8+h7y+z6i.W5j+z6i.w03)}
,"form":{"wrapper":"DTE_Form","content":(R73+V7R+e63+W1+i2j+z6i.W5j+h7y+z6i.W5j+z6i.w03),"tag":"","info":(Z7R+d9R+M7j+p1R+i2j+E03+p8R+v9R+z6i.W5j+z6i.X6j+i2j),"error":"DTE_Form_Error","buttons":"DTE_Form_Buttons","button":(i9j+z6i.w03+z6i.W5j)}
,"field":{"wrapper":"DTE_Field","typePrefix":(R73+G7R+M7j+p1R+P7j+z6i.S8j+z6i.V9j+M7j+j5R+W9R+I1j),"namePrefix":(R73+G7R+M7j+V6y+O8y+V5j+p5j+z6i.x6j+M7j),"label":"DTE_Label","input":(Z7R+j5R+G7R+O9+P4j+z6i.x6j+z6i.S8j+D3R+B3j+B33+z6i.w03),"inputControl":(t03+E+z6i.x6j+x1R+v9R+z6i.W5j+R6R+O8+z6i.w03+L73+z6i.S8j),"error":"DTE_Field_StateError","msg-label":"DTE_Label_Info","msg-error":"DTE_Field_Error","msg-message":(z0y+t8j+z6i.V9j+M7j+W3j+j03+d2j+z6i.x6j),"msg-info":(t03+E+z6i.x6j+z6i.S8j+W0y+z6i.W5j+z6i.X6j+i2j),"multiValue":(p5j+B33+z6i.S8j+I1y+p9y+k33+Y33+B33+z6i.x6j),"multiInfo":"multi-info","multiRestore":"multi-restore","multiNoEdit":(y6j+K1R+P4j+p9y+z6i.W5j+i2j+G7R+x6R+z6i.w03),"disabled":(E1R+s4j)}
,"actions":{"create":(Z7R+j5R+x2+C3R+U5y+P4j+Z93+A7R+E03+Y9j+z6i.w03+z6i.x6j),"edit":(E8y+c9j+z6i.w03+Q4j+z6i.W5j+M7j+G7R+H13),"remove":"DTE_Action_Remove"}
,"inline":{"wrapper":(R73+G7R+M2+Z7R+d9R+f1R+N1),"liner":(R73+x2+v9R+z6i.W5j+z6i.S8j+j6j+I1j+p1R+W9j),"buttons":(Z7R+c93+v9R+A5R+w2j+p2j)}
,"bubble":{"wrapper":"DTE DTE_Bubble","liner":(R73+x2+q3R+B33+T0j+z6i.x6j+M7j+I6R+P4j+z6i.W5j+z6i.x6j+E03),"table":(Z7R+y9R+z6i.x6j+M7j+u9j+c9+z6i.x6j),"close":(P4j+c9j+i2j+z6i.W5j+M2+c9j+d3R+s3),"pointer":(Z7R+j5R+n9R+J9R+z6i.S8j+I1j+j5R+M2j+y8+z6i.S8j+z6i.x6j),"bg":(Z7R+j5R+x2+q3R+s6j+f0R+X8j+E8j+z7y+x33)}
}
;(function(){var S8="ngle",a6R="veSi",Y7y="gl",K4R="Si",O7y="editSingle",K2y="Sing",z7='mo',P43='tons',j1y='ows',u7y="formMessage",v9y="tl",w9y='ns',B2='utto',f3j="i18",o1j="tons",A4="formButtons",M7R="sing",r43="sele",k6="tor_ed",X5j="r_cr",N2="NS",T2y="BU";if(DataTable[(p7y+z6i.S8j+z5R+i2j+i2j+z6i.S8j+j03)]){var ttButtons=DataTable[C43][(T2y+j5R+j5R+s4R+N2)],ttButtonBase={sButtonText:null,editor:null,formTitle:null}
;ttButtons[(Z6j+P4j+z6i.w03+i2j+X5j+z6i.x6j+S1y)]=$[n7R](true,ttButtons[(z6i.w03+z6i.x6j+C9y)],ttButtonBase,{formButtons:[{label:null,fn:function(e){this[V3y]();}
}
],fnClick:function(button,config){var u3="rmB",editor=config[(z6i.x6j+z6i.V9j+P4j+z6i.w03+i2j+E03)],i18nCreate=editor[U7][S2j],buttons=config[(z6i.X6j+i2j+u3+B33+z6i.w03+z6i.w03+p2j)];if(!buttons[0][H2R]){buttons[0][H2R]=i18nCreate[(R8+S9+P4j+z6i.w03)];}
editor[S2j]({title:i18nCreate[(z6i.w03+P4j+z6i.w03+z6i.S8j+z6i.x6j)],buttons:buttons}
);}
}
);ttButtons[(z6i.x6j+x6R+k6+P4j+z6i.w03)]=$[(z6i.x6j+v73+s13)](true,ttButtons[(r43+U5y+M7j+M7R+E5y)],ttButtonBase,{formButtons:[{label:null,fn:function(e){this[(R8+i9j+M0j+z6i.w03)]();}
}
],fnClick:function(button,config){var Y2y="xes",f9y="Ind",w1="tSele",selected=this[(Y7+l1R+z6i.x6j+w1+c9j+z6i.w03+z6i.x6j+z6i.V9j+f9y+z6i.x6j+Y2y)]();if(selected.length!==1){return ;}
var editor=config[(Z6j+P4j+w6y+E03)],i18nEdit=editor[(P4j+l1y)][S3R],buttons=config[A4];if(!buttons[0][(z6i.S8j+z6i.F8j+t8j)]){buttons[0][(z6i.S8j+z6i.S1j+i9j+z6i.x6j+z6i.S8j)]=i18nEdit[(l93+z6i.w03)];}
editor[S3R](selected[0],{title:i18nEdit[(Z4y)],buttons:buttons}
);}
}
);ttButtons[(z6i.x6j+z6i.V9j+P4j+z6i.w03+S5+M7j+E03+z6i.x6j+p5j+i2j+I9j)]=$[n7R](true,ttButtons[K9],ttButtonBase,{question:null,formButtons:[{label:null,fn:function(e){var that=this;this[V3y](function(json){var O3="fnSelectNone",V0R="Data",I7="tI",W0j="TableToo",q9y="data",tt=$[Y7][(q9y+j5R+z6i.S1j+i9j+z6i.S8j+z6i.x6j)][(W0j+I7R)][(Y7+l1R+z6i.x6j+I7+f63+z6i.w03+a73+X7y)]($(that[j03][(z6i.w03+z6i.S1j+i9j+E5y)])[(V0R+p7y+z6i.S8j+z6i.x6j)]()[(P0+E5y)]()[C0R]());tt[O3]();}
);}
}
],fnClick:function(button,config){var v1="abe",I4y="mB",f03="cte",L4="tS",rows=this[(z6i.X6j+z6i.W5j+l1R+z6i.x6j+L4+r1R+f03+z6i.V9j+v9R+z6i.W5j+C1R+v73+l03)]();if(rows.length===0){return ;}
var editor=config[Z0j],i18nRemove=editor[U7][F1],buttons=config[(u8R+I4y+K2R+o1j)],question=typeof i18nRemove[B7]===(q0+z9j+N1j)?i18nRemove[B7]:i18nRemove[B7][rows.length]?i18nRemove[(c9j+U43+P4j+C33)][rows.length]:i18nRemove[B7][M7j];if(!buttons[0][(z6i.S8j+z6i.S1j+i9j+t8j)]){buttons[0][(z6i.S8j+v1+z6i.S8j)]=i18nRemove[V3y];}
editor[(E03+z6i.x6j+p5j+q8R)](rows,{message:question[(E03+z6i.x6j+h2j+z6i.S8j+z6i.S1j+c9j+z6i.x6j)](/%d/g,rows.length),title:i18nRemove[(I1y+z6i.w03+E5y)],buttons:buttons}
);}
}
);}
var _buttons=DataTable[r7j][(Y5+o1j)];$[(a1y+z6i.V9j)](_buttons,{create:{text:function(dt,node,config){var o0R="edito";return dt[(f3j+z6i.W5j)]('buttons.create',config[(o0R+E03)][(U7)][(S2j)][d13]);}
,className:(z6i.w73+B2+w9y+C7R+L13+M6j),editor:null,formButtons:{text:function(editor){return editor[U7][S2j][(j03+f3R+p5j+P4j+z6i.w03)];}
,action:function(e){var u2y="bmit";this[(j03+B33+u2y)]();}
}
,formMessage:null,formTitle:null,action:function(e,dt,node,config){var b5j="eate",W13="formTitle",q6="Me",a0y="mBu",h8="itor",editor=config[(Z6j+h8)],buttons=config[(z6i.X6j+i2j+E03+a0y+j8y+p2j)];editor[(c9j+d5j+S1y)]({buttons:config[(c7+C33+a3j+z6i.w03+z6i.w03+p2j)],message:config[(c7+E03+p5j+q6+j03+j03+z6i.S1j+w6j+z6i.x6j)],title:config[W13]||editor[(P4j+M6y+u5y+z6i.W5j)][(c9j+E03+b5j)][(z6i.w03+P4j+v9y+z6i.x6j)]}
);}
}
,edit:{extend:'selected',text:function(dt,node,config){return dt[(f3j+z6i.W5j)]('buttons.edit',config[(z6i.x6j+z6i.V9j+P4j+z6i.w03+i2j+E03)][(P4j+n2+z6i.W5j)][(z6i.x6j+x6R+z6i.w03)][d13]);}
,className:'buttons-edit',editor:null,formButtons:{text:function(editor){return editor[(P4j+l1y)][(Z6j+P4j+z6i.w03)][V3y];}
,action:function(e){this[(x7j+p5j+P4j+z6i.w03)]();}
}
,formMessage:null,formTitle:null,action:function(e,dt,node,config){var j7R="mT",P63="exes",editor=config[(z6i.x6j+z6i.V9j+P4j+z6i.w03+i2j+E03)],rows=dt[H93]({selected:true}
)[(j6j+z6i.V9j+P63)](),columns=dt[P5R]({selected:true}
)[a8](),cells=dt[(c9j+N4R)]({selected:true}
)[a8](),items=columns.length||cells.length?{rows:rows,columns:columns,cells:cells}
:rows;editor[(z6i.x6j+x6R+z6i.w03)](items,{message:config[u7y],buttons:config[A4],title:config[(u8R+j7R+P4j+z6i.w03+E5y)]||editor[U7][S3R][(z6i.w03+P4j+z6i.w03+z6i.S8j+z6i.x6j)]}
);}
}
,remove:{extend:'selected',limitTo:[(V0+j1y)],text:function(dt,node,config){return dt[U7]((D7+t43+q0+w7R+V0+z6i.w13+W43+z6i.u83+R7+z6i.w13),config[(R93+c3j)][(F1y+i7y)][F1][(i9j+B33+z6i.w03+V2R)]);}
,className:(j3y+P43+C7R+V0+z6i.w13+z7+R7+z6i.w13),editor:null,formButtons:{text:function(editor){return editor[U7][F1][(x7j+M0j+z6i.w03)];}
,action:function(e){this[V3y]();}
}
,formMessage:function(editor,dt){var F2='ri',T4="inde",rows=dt[(E03+i2j+D1)]({selected:true}
)[(T4+v73+z6i.x6j+j03)](),i18n=editor[U7][(E03+c5j+i2j+I9j)],question=typeof i18n[B7]===(q0+J3+F2+t43+I93)?i18n[B7]:i18n[B7][rows.length]?i18n[B7][rows.length]:i18n[(p4y+z6i.W5j+z6i.X6j+P4j+C33)][M7j];return question[(S1R+V4y+X7y)](/%d/g,rows.length);}
,formTitle:null,action:function(e,dt,node,config){var N3j="emove",w9="mTi",b5="ows",editor=config[(R93+z6i.w03+S5)];editor[(E03+z6i.x6j+p5j+i2j+I9j)](dt[(E03+b5)]({selected:true}
)[(h1+z6i.x6j+v73+l03)](),{buttons:config[A4],message:config[u7y],title:config[(u8R+w9+v9y+z6i.x6j)]||editor[U7][(E03+N3j)][Z4y]}
);}
}
}
);_buttons[(R93+z6i.w03+K2y+z6i.S8j+z6i.x6j)]=$[n7R]({}
,_buttons[(Z6j+P4j+z6i.w03)]);_buttons[O7y][n7R]='selectedSingle';_buttons[(d5j+p5j+i2j+I9j+K4R+z6i.W5j+Y7y+z6i.x6j)]=$[n7R]({}
,_buttons[F1]);_buttons[(A8j+a6R+S8)][(z6i.x6j+v73+z6i.w03+z6i.x6j+z6i.W5j+z6i.V9j)]='selectedSingle';}
());Editor[(z6i.X6j+P7j+z6i.S8j+H8y+z73+h2j+z6i.x6j+j03)]={}
;Editor[(K2+z5R+U6j+z6i.x6j)]=function(input,opts){var R0y="_con",n0j="calendar",t5="ppend",z8R="Of",i0R="ins",i5R="teTime",b4y='tei',C='me',M6='itl',c43='onds',t5R="previous",f4='onL',t93="sed",i3="js",s7R="itho",d4=": ",o7y="rma";this[c9j]=$[(p13+q3+z6i.V9j)](true,{}
,Editor[W0][(z6i.V9j+z6i.x6j+g63+B33+K1R+j03)],opts);var classPrefix=this[c9j][o6R],i18n=this[c9j][(P4j+M6y+i7y)];if(!window[I8y]&&this[c9j][(z6i.X6j+i2j+o7y+z6i.w03)]!=='YYYY-MM-DD'){throw (G7R+z6i.V9j+P4j+z6i.w03+i2j+E03+M2+z6i.V9j+z6i.S1j+z6i.w03+A33+P4j+p5j+z6i.x6j+d4+j2R+s7R+B33+z6i.w03+M2+p5j+u8+z6i.x6j+d43+i3+M2+i2j+z6i.W5j+G9R+M2+z6i.w03+K3R+M2+z6i.X6j+i2j+E03+p5j+X93+F9+c0j+c0j+c0j+c0j+p9y+m6R+m6R+p9y+Z7R+Z7R+d7j+c9j+z6i.S1j+z6i.W5j+M2+i9j+z6i.x6j+M2+B33+t93);}
var timeBlock=function(type){var s2j='onD',v4R="evio",h4j='eblock';return (o5R+V13+d63+R7+Q5y+L13+m9R+w2)+classPrefix+(C7R+J3+c6+h4j+r9)+(o5R+V13+d63+R7+Q5y+L13+v9j+s1R+w2)+classPrefix+(C7R+d63+a6+M0R+r9)+'<button>'+i18n[(N2y+v4R+B33+j03)]+'</button>'+(y9+V13+d63+R7+i2R)+'<div class="'+classPrefix+'-label">'+(o5R+q0+B6y+q4)+(o5R+q0+I8+I03+Q5y+L13+F43+P73+s1R+w2)+classPrefix+'-'+type+(d2)+(y9+V13+d63+R7+i2R)+(o5R+V13+Z5+Q5y+L13+m9R+w2)+classPrefix+(C7R+d63+L13+s2j+j8R+t43+r9)+(o5R+z6i.w73+P3+J3+J3+k9R+i2R)+i18n[(X33+v73+z6i.w03)]+'</button>'+'</div>'+'</div>';}
,gap=function(){var K='>:</';return (o5R+q0+Z3j+t43+K+q0+B6y+i2R);}
,structure=$('<div class="'+classPrefix+'">'+(o5R+V13+d63+R7+Q5y+L13+F43+P73+s1R+w2)+classPrefix+(C7R+V13+P73+J3+z6i.w13+r9)+(o5R+V13+d63+R7+Q5y+L13+v9j+s1R+w2)+classPrefix+(C7R+J3+d63+J3+o4j+r9)+(o5R+V13+d63+R7+Q5y+L13+v9j+s1R+w2)+classPrefix+(C7R+d63+L13+f4+z6i.w13+o93+J3+r9)+(o5R+z6i.w73+P3+J3+J3+z6i.u83+t43+i2R)+i18n[t5R]+(y9+z6i.w73+L83+J3+z6i.u83+t43+i2R)+(y9+V13+Z5+i2R)+(o5R+V13+Z5+Q5y+L13+v9j+s1R+w2)+classPrefix+'-iconRight">'+(o5R+z6i.w73+L83+J3+k9R+i2R)+i18n[(X33+C9y)]+(y9+z6i.w73+p7R+z6i.u83+t43+i2R)+(y9+V13+d63+R7+i2R)+'<div class="'+classPrefix+(C7R+F43+P73+z6i.w73+z6i.w13+F43+r9)+'<span/>'+(o5R+q0+I8+I03+Q5y+L13+l7y+q0+w2)+classPrefix+(C7R+W43+z6i.u83+t43+J3+r93+d2)+(y9+V13+Z5+i2R)+'<div class="'+classPrefix+(C7R+F43+t4+I8+r9)+(o5R+q0+T+P73+t43+q4)+(o5R+q0+z6i.w13+o4j+z6i.U4j+Q5y+L13+v9j+q0+q0+w2)+classPrefix+(C7R+i1+z6i.w13+P73+V0+d2)+'</div>'+'</div>'+'<div class="'+classPrefix+(C7R+L13+P73+o4j+x0y+P73+V0+d2)+'</div>'+(o5R+V13+d63+R7+Q5y+L13+v9j+q0+q0+w2)+classPrefix+'-time">'+timeBlock('hours')+gap()+timeBlock('minutes')+gap()+timeBlock((V5y+L13+c43))+timeBlock('ampm')+(y9+V13+Z5+i2R)+(o5R+V13+Z5+Q5y+L13+F43+P73+s1R+w2)+classPrefix+(C7R+z6i.w13+n7y+w6R+d2)+'</div>');this[(B0)]={container:structure,date:structure[(c0+x33)]('.'+classPrefix+'-date'),title:structure[a8R]('.'+classPrefix+(C7R+J3+M6+z6i.w13)),calendar:structure[(z6i.X6j+P4j+x33)]('.'+classPrefix+(C7R+L13+P73+F43+H5+V13+N7y)),time:structure[a8R]('.'+classPrefix+(C7R+J3+d63+C)),error:structure[(z6i.X6j+h1)]('.'+classPrefix+'-error'),input:$(input)}
;this[j03]={d:null,display:null,namespace:(u6+u5+V0+C7R+V13+P73+b4y+W43+z6i.w13+C7R)+(Editor[(l43+i5R)][(M7j+i0R+D0y+E33)]++),parts:{date:this[c9j][F63][U9j](/[YMD]|L(?!T)|l/)!==null,time:this[c9j][F63][(r8R+z6i.w03+b1y)](/[Hhm]|LT|LTS/)!==null,seconds:this[c9j][(z6i.X6j+i2j+E03+p5j+z6i.S1j+z6i.w03)][(P4j+x33+p13+z8R)]('s')!==-1,hours12:this[c9j][(c7+C33+X93)][(p5j+z6i.S1j+z6i.w03+c9j+c4j)](/[haA]/)!==null}
}
;this[(z6i.V9j+u8)][G73][o6y](this[(z6i.V9j+u8)][(z6i.V9j+z6i.S1j+h7y)])[(z6i.S1j+t5)](this[(z6i.V9j+i2j+p5j)][(z6i.w03+S03)])[(z6i.S1j+H1j+x33)](this[(z6i.V9j+i2j+p5j)].error);this[(Y8R+p5j)][(z6i.V9j+X93+z6i.x6j)][o6y](this[B0][Z4y])[(z6i.S1j+h2j+Y6y+x33)](this[B0][n0j]);this[(R0y+g4+E03+B33+c9j+z6i.w03+S5)]();}
;$[n7R](Editor.DateTime.prototype,{destroy:function(){this[B4]();this[(Y8R+p5j)][G73][v03]().empty();this[(z6i.V9j+i2j+p5j)][Q0][v03]((w7R+z6i.w13+V13+d63+J3+w6R+C7R+V13+P73+J3+z6i.w13+U3j+W43+z6i.w13));}
,errorMsg:function(msg){var error=this[(z6i.V9j+u8)].error;if(msg){error[(c4j+A6y+z6i.S8j)](msg);}
else{error.empty();}
}
,hide:function(){this[(h4y+P4j+C1R)]();}
,max:function(date){var G0j="maxDate";this[c9j][G0j]=date;this[i4j]();this[(r4+x8j+a73+z6i.V9j+T03)]();}
,min:function(date){var K73="ande",G93="minDate";this[c9j][G93]=date;this[i4j]();this[(r4+x8j+K73+E03)]();}
,owns:function(node){return $(node)[p6y]()[(s8y+z6i.w03+z6i.x6j+E03)](this[(z6i.V9j+u8)][G73]).length>0;}
,val:function(set,write){var g2R="lande",C8="etCa",y7R="setUTCDate",y8R="_date",U5R="oDat",g1y="alid",P6y="ocale",k1j="mom",W6="mome";if(set===undefined){return this[j03][z6i.V9j];}
if(set instanceof Date){this[j03][z6i.V9j]=this[F73](set);}
else if(set===null||set===''){this[j03][z6i.V9j]=null;}
else if(typeof set==='string'){if(window[(W6+d43)]){var m=window[(k1j+z6i.x6j+z6i.W5j+z6i.w03)][(B33+z6i.w03+c9j)](set,this[c9j][F63],this[c9j][(t7j+p5j+z6i.x6j+d43+I6R+P6y)],this[c9j][U2]);this[j03][z6i.V9j]=m[(C8j+c2R+g1y)]()?m[(z6i.w03+U5R+z6i.x6j)]():null;}
else{var match=set[(U9j)](/(\d{4})\-(\d{2})\-(\d{2})/);this[j03][z6i.V9j]=match?new Date(Date[(e3y)](match[1],match[2]-1,match[3])):null;}
}
if(write||write===undefined){if(this[j03][z6i.V9j]){this[(M7j+Y73+M2j+h7y+s4R+B33+z6i.w03+h2j+K2R)]();}
else{this[(z6i.V9j+i2j+p5j)][(P4j+Q63+K2R)][(k33+Y33)](set);}
}
if(!this[j03][z6i.V9j]){this[j03][z6i.V9j]=this[(y8R+U03+m5R+u3y)](new Date());}
this[j03][M43]=new Date(this[j03][z6i.V9j][(z6i.w03+i2j+p5R+z6i.w03+M2j+h73)]());this[j03][M43][y7R](1);this[(M7j+j03+A33+j5R+G8j+z6i.S8j+z6i.x6j)]();this[(M7j+j03+C8+g2R+E03)]();this[(G0R+z6i.x6j+z6i.w03+k8j+p5j+z6i.x6j)]();}
,_constructor:function(){var x7R="_w",m8y="_setCalander",d8y="_setTitle",k63="_correctMonth",G4='selec',x7y='atet',j6R='cus',q4j="amPm",R3R="nds",F83="sTi",f7="minutesIncrement",E6="s12",e5y="hou",y83="part",y13='hour',q43="_optionsTime",R='mebl',x9j="hildre",w3y="hours12",c2j="emo",M3R="hildren",T9='eb',h0='ateti',U8R="ildr",k3j="seconds",T6='non',v13='spl',p7="rts",R1y="onChange",that=this,classPrefix=this[c9j][o6R],container=this[(z6i.V9j+u8)][(p4y+z6i.W5j+z6i.w03+z6i.S1j+N1+E03)],i18n=this[c9j][U7],onChange=this[c9j][R1y];if(!this[j03][(s1y+p7)][Z1y]){this[(Y8R+p5j)][(Z1y)][n43]((g13+v13+E6y),(T6+z6i.w13));}
if(!this[j03][(h2j+z6i.S1j+E03+z6i.w03+j03)][(z6i.w03+S03)]){this[B0][(z6i.w03+S03)][n43]('display','none');}
if(!this[j03][(s1y+N13+j03)][k3j]){this[B0][(I1y+p5j+z6i.x6j)][(c9j+c4j+U8R+z6i.x6j+z6i.W5j)]((p+w7R+z6i.w13+V13+v8+z6i.u83+V0+C7R+V13+h0+W43+z6i.w13+C7R+J3+d63+W43+T9+F43+J6R))[Q03](2)[F1]();this[(B0)][S4j][(c9j+M3R)]('span')[(Q03)](1)[(E03+c2j+I9j)]();}
if(!this[j03][L1y][w3y]){this[(z6i.V9j+u8)][(I1y+p5j+z6i.x6j)][(c9j+x9j+z6i.W5j)]((p+w7R+z6i.w13+q5j+C7R+V13+B1y+d0y+c6+z6i.w13+C7R+J3+d63+R+z6i.u83+L13+D63))[(V4y+g4)]()[F1]();}
this[i4j]();this[q43]((y13+q0),this[j03][(y83+j03)][(e5y+E03+E6)]?12:24,1);this[q43]('minutes',60,this[c9j][f7]);this[(M7j+p5+z6i.w03+P4j+i2j+z6i.W5j+F83+p5j+z6i.x6j)]('seconds',60,this[c9j][(j03+z6i.x6j+p4y+R3R+v9R+k03+i6j+O5j+z6i.w03)]);this[t5y]((P73+W43+Y4j),[(l0y),(T+W43)],i18n[q4j]);this[(Y8R+p5j)][(P4j+z6i.W5j+j0R+z6i.w03)][(O8)]((W2y+j6R+w7R+z6i.w13+o8+V0+C7R+V13+E73+J3+F3R+Q5y+L13+v8j+Z7j+w7R+z6i.w13+V13+u5+V0+C7R+V13+x7y+c6+z6i.w13),function(){var E8="ainer";if(that[(z6i.V9j+i2j+p5j)][(p4y+d43+E8)][C8j](':visible')||that[(Y8R+p5j)][(P4j+c3+z6i.w03)][(P4j+j03)]((H8R+V13+d63+q0+P73+Y3R+z6i.w13+V13))){return ;}
that[s73](that[(z6i.V9j+i2j+p5j)][Q0][(s73)](),false);that[(G0R+c4j+u0y)]();}
)[(i2j+z6i.W5j)]((b9R+i1+I63+w7R+z6i.w13+V13+d63+J3+w6R+C7R+V13+P73+J3+d0y+F3R),function(){if(that[B0][(c9j+O8+z6i.w03+z6i.S1j+N1+E03)][C8j](':visible')){that[(k33+Y33)](that[(B0)][(P4j+F2j)][(k33+z6i.S1j+z6i.S8j)](),false);}
}
);this[(B0)][G73][(i2j+z6i.W5j)]((L13+H5y+c8R),(G4+J3),function(){var n0y="Clas",L8j="riteOu",o4y="etUTCM",q9R='nut',T13="_writeOutput",p9R="UTCHours",F6="ntain",V4j="sC",I3j="etTitle",H3y="setUTCFullYear",Q0j='ear',M8R="setC",A3y="hasCla",select=$(this),val=select[(s73)]();if(select[(A3y+j03+j03)](classPrefix+'-month')){that[k63](that[j03][(x6R+N9y+i43)],val);that[d8y]();that[(M7j+M8R+z6i.S1j+z6i.S8j+z6i.S1j+z6i.W5j+C1R+E03)]();}
else if(select[F3j](classPrefix+(C7R+i1+Q0j))){that[j03][(z6i.V9j+P4j+j03+S8y+z6i.S1j+z73)][H3y](val);that[(G0R+I3j)]();that[m8y]();}
else if(select[F3j](classPrefix+(C7R+r93+z6i.u83+h43+q0))||select[(c4j+z6i.S1j+V4j+V4y+j03+j03)](classPrefix+'-ampm')){if(that[j03][L1y][w3y]){var hours=$(that[B0][(p4y+F6+z6i.x6j+E03)])[(z6i.X6j+P4j+z6i.W5j+z6i.V9j)]('.'+classPrefix+'-hours')[s73]()*1,pm=$(that[B0][(p4y+d43+A03+z6i.W5j+z6i.x6j+E03)])[a8R]('.'+classPrefix+'-ampm')[s73]()===(Y4j);that[j03][z6i.V9j][l0R](hours===12&&!pm?0:pm&&hours!==12?hours+12:hours);}
else{that[j03][z6i.V9j][(j03+A33+p9R)](val);}
that[(M7j+s3+z6i.w03+j5R+U6j+z6i.x6j)]();that[T13](true);onChange();}
else if(select[(f2y+j03+A7R+R6y)](classPrefix+(C7R+W43+d63+q9R+z6i.w13+q0))){that[j03][z6i.V9j][(j03+o4y+j6j+B33+k1)](val);that[(M7j+j03+A33+k8j+p5j+z6i.x6j)]();that[(x7R+L8j+z6i.w03+h2j+B33+z6i.w03)](true);onChange();}
else if(select[(c4j+J93+n0y+j03)](classPrefix+'-seconds')){that[j03][z6i.V9j][z13](val);that[(M7j+R2j+j5R+P4j+p5j+z6i.x6j)]();that[T13](true);onChange();}
that[(z6i.V9j+u8)][(P4j+z6i.W5j+h2j+K2R)][g33]();that[(M7j+w5y+j03+P4j+z6i.w03+P4j+i2j+z6i.W5j)]();}
)[O8]((L13+F43+r3+D63),function(e){var v93="tpu",d7y="etU",R7j="setUTCMonth",o3R="Ful",z8j="hang",X1y="dI",V7y="edInd",I2R="tedInd",g4j="selected",B="selectedIndex",l8y='lec',F4="nth",y7y='nRi',H6j="Ca",D9j="setU",q73="spla",J3R='ft',v3y='Le',n2R="stopPropagation",nodeName=e[(z6i.w03+z6i.S1j+A2j+A33)][c8j][i9y]();if(nodeName===(q0+K2j+J3)){return ;}
e[n2R]();if(nodeName===(j3y+J3+z6i.u83+t43)){var button=$(e[d5y]),parent=button.parent(),select;if(parent[F3j]('disabled')){return ;}
if(parent[F3j](classPrefix+(C7R+d63+a9j+t43+v3y+J3R))){that[j03][(x6R+q73+z73)][(D9j+j5R+A7R+m6R+t2j+c4j)](that[j03][M43][A4R]()-1);that[(M7j+j03+z6i.x6j+z6i.w03+j5R+G8j+E5y)]();that[(r4+H6j+z6i.S8j+a73+Z63)]();that[B0][Q0][(g33)]();}
else if(parent[F3j](classPrefix+(C7R+d63+a9j+y7y+I93+r93+J3))){that[k63](that[j03][M43],that[j03][(x6R+D1R)][(w6j+A33+e3y+m6R+i2j+F4)]()+1);that[d8y]();that[m8y]();that[(z6i.V9j+i2j+p5j)][(P4j+z6i.W5j+E6j)][(z6i.X6j+l1+s5R)]();}
else if(parent[(c4j+J93+t7y+j03+j03)](classPrefix+'-iconUp')){select=parent.parent()[a8R]((q0+z6i.w13+l8y+J3))[0];select[B]=select[(g4j+J3y+z6i.V9j+p13)]!==select[K0R].length-1?select[(j03+z6i.x6j+z6i.S8j+G9j+I2R+z6i.x6j+v73)]+1:0;$(select)[R83]();}
else if(parent[(c4j+J93+o2j+z6i.S1j+j03+j03)](classPrefix+'-iconDown')){select=parent.parent()[(c0+z6i.W5j+z6i.V9j)]((B6+z6i.w13+L13+J3))[0];select[(s3+z6i.S8j+M1R+V7y+z6i.x6j+v73)]=select[(j03+v6y+z6i.w03+z6i.x6j+X1y+h9+v73)]===0?select[(i2j+h2j+I1y+i2j+z6i.W5j+j03)].length-1:select[B]-1;$(select)[(c9j+z8j+z6i.x6j)]();}
else{if(!that[j03][z6i.V9j]){that[j03][z6i.V9j]=that[(M7j+z6i.V9j+X93+z5R+i2j+m5R+u3y)](new Date());}
that[j03][z6i.V9j][(j03+A33+e3y+l43+h7y)](1);that[j03][z6i.V9j][(s3+V4+j5R+A7R+o3R+z6i.S8j+c0j+L3)](button.data((G13+V0)));that[j03][z6i.V9j][R7j](button.data('month'));that[j03][z6i.V9j][(j03+d7y+j5R+A7R+Z7R+z6i.S1j+h7y)](button.data('day'));that[(x7R+M2j+z6i.w03+z6i.x6j+s4R+B33+v93+z6i.w03)](true);if(!that[j03][(s1y+E03+z6i.w03+j03)][S4j]){setTimeout(function(){that[B4]();}
,10);}
else{that[m8y]();}
onChange();}
}
else{that[(z6i.V9j+i2j+p5j)][(P4j+z6i.W5j+h2j+B33+z6i.w03)][(z6i.X6j+i2j+c9j+s5R)]();}
}
);}
,_compareDates:function(a,b){var E43="_dateToUtcString",X9="ing",x2R="tcS",y43="oU";return this[(M7j+z6i.V9j+z6i.S1j+z6i.w03+z5R+y43+x2R+l4y+X9)](a)===this[E43](b);}
,_correctMonth:function(date,month){var t1j="etUTC",D5R="tUTCM",z0j="etUTCD",days=this[l2y](date[h6R](),month),correctDays=date[(w6j+z0j+X93+z6i.x6j)]()>days;date[(j03+z6i.x6j+D5R+z0R)](month);if(correctDays){date[(j03+t1j+l43+h7y)](days);date[(j03+z6i.x6j+z6i.w03+e3y+m6R+O8+z6i.w03+c4j)](month);}
}
,_daysInMonth:function(year,month){var isLeap=((year%4)===0&&((year%100)!==0||(year%400)===0)),months=[31,(isLeap?29:28),31,30,31,30,31,31,30,31,30,31];return months[month];}
,_dateToUtc:function(s){var P9R="Se",S0j="getHours",J9="tM";return new Date(Date[(m5R+j5R+A7R)](s[Z3y](),s[(w6j+z6i.x6j+J9+i2j+z6i.W5j+z6i.w03+c4j)](),s[(K0y+z6i.w03+Z7R+X93+z6i.x6j)](),s[S0j](),s[(w6j+z6i.x6j+z6i.w03+W63+l03)](),s[(w6j+A33+P9R+p4y+x33+j03)]()));}
,_dateToUtcString:function(d){var P5="TCDate",n3="_pad",g8R="Fu";return d[(w6j+z6i.x6j+Y4+g8R+z6i.S8j+z6i.S8j+c0j+z6i.x6j+z6i.S1j+E03)]()+'-'+this[(n3)](d[(V9R+e3y+m6R+z0R)]()+1)+'-'+this[(M7j+h2j+a5j)](d[(K0y+z6i.w03+m5R+P5)]());}
,_hide:function(){var Q43="det",namespace=this[j03][w0y];this[(z6i.V9j+i2j+p5j)][G73][(Q43+a6y)]();$(window)[(i2j+z6i.X6j+z6i.X6j)]('.'+namespace);$(document)[(i2j+h)]((b9R+i1+V13+z6i.u83+n7+t43+w7R)+namespace);$('div.DTE_Body_Content')[v03]('scroll.'+namespace);$((F7R+V13+i1))[v03]('click.'+namespace);}
,_hours24To12:function(val){return val===0?12:val>12?val-12:val;}
,_htmlDay:function(day){var p2y='tton',k5j="day",A6="cted",x6y="today",Z0R='bled',a83="pus";if(day.empty){return (o5R+J3+V13+Q5y+L13+v9j+s1R+w2+z6i.w13+W43+T+J3+i1+C6+J3+V13+i2R);}
var classes=[(r03+i1)],classPrefix=this[c9j][o6R];if(day[D5j]){classes[(a83+c4j)]((b0+P73+Z0R));}
if(day[x6y]){classes[(j0R+g7)]((r1j+V13+E6y));}
if(day[(j03+z6i.x6j+E5y+A6)]){classes[l6R]((q0+z6i.w13+F43+z6i.w13+z6i.U4j+z6i.w13+V13));}
return '<td data-day="'+day[(k5j)]+'" class="'+classes[H2j](' ')+'">'+(o5R+z6i.w73+P3+e6j+z6i.u83+t43+Q5y+L13+F43+P73+s1R+w2)+classPrefix+(C7R+z6i.w73+P3+J3+S63+Q5y)+classPrefix+'-day" type="button" '+(V13+P73+J3+P73+C7R+i1+z6i.w13+N7y+w2)+day[(z73+L3)]+'" data-month="'+day[(t7j+d43+c4j)]+(y73+V13+B1y+P73+C7R+V13+E6y+w2)+day[(L7R+z73)]+(r9)+day[(z6i.V9j+z6i.S1j+z73)]+(y9+z6i.w73+P3+p2y+i2R)+'</td>';}
,_htmlMonth:function(year,month){var q6y="_htmlMonthHead",X9j='loc',U="jo",o13="fY",z8="eek",d9y="ift",B5R="mb",S43="kN",V2y="owWee",z2="lDay",d7="_ht",z4R="ays",K4y="disa",K03="pare",E83="com",f5="Sec",f13="TCMinu",b6y="Hour",F8="Mi",t0y="axD",e2j="inD",w63="rstD",now=this[F73](new Date()),days=this[l2y](year,month),before=new Date(Date[e3y](year,month,1))[(K0y+z6i.w03+m5R+j5R+A7R+Z7R+z6i.S1j+z73)](),data=[],row=[];if(this[c9j][(z6i.X6j+K8j+g4+l43+z73)]>0){before-=this[c9j][(z6i.X6j+P4j+w63+z6i.S1j+z73)];if(before<0){before+=7;}
}
var cells=days+before,after=cells;while(after>7){after-=7;}
cells+=7-after;var minDate=this[c9j][(p5j+e2j+X93+z6i.x6j)],maxDate=this[c9j][(p5j+t0y+S1y)];if(minDate){minDate[l0R](0);minDate[(j03+A33+m5R+t7R+F8+z6i.W5j+B33+k1)](0);minDate[z13](0);}
if(maxDate){maxDate[(s3+z6i.w03+m5R+t7R+b6y+j03)](23);maxDate[(s3+V4+f13+k1)](59);maxDate[(j03+z6i.x6j+z6i.w03+f5+i2j+z6i.W5j+z6i.V9j+j03)](59);}
for(var i=0,r=0;i<cells;i++){var day=new Date(Date[(m5R+t7R)](year,month,1+(i-before))),selected=this[j03][z6i.V9j]?this[(M7j+c9j+u8+l3+z6i.x6j+Z7R+S1y+j03)](day,this[j03][z6i.V9j]):false,today=this[(M7j+E83+K03+Z7R+z6i.S1j+z6i.w03+l03)](day,now),empty=i<before||i>=(days+before),disabled=(minDate&&day<minDate)||(maxDate&&day>maxDate),disableDays=this[c9j][(K4y+i9j+z6i.S8j+F1R+z4R)];if($[(C8j+C3R+E03+E03+z6i.S1j+z73)](disableDays)&&$[y4j](day[(K0y+V4+j5R+A7R+Z7R+z6i.S1j+z73)](),disableDays)!==-1){disabled=true;}
else if(typeof disableDays==='function'&&disableDays(day)===true){disabled=true;}
var dayConfig={day:1+(i-before),month:month,year:year,selected:selected,today:today,disabled:disabled,empty:empty}
;row[(j0R+g7)](this[(d7+p5j+z2)](dayConfig));if(++r===7){if(this[c9j][(j03+c4j+V2y+S43+B33+B5R+T03)]){row[(D4R+j03+c4j+d9y)](this[(M7j+Q4R+a7j+j2R+z8+s4R+o13+z6i.x6j+q13)](i-before,month,year));}
data[(h2j+W6R)]((o5R+J3+V0+i2R)+row[(U+j6j)]('')+(y9+J3+V0+i2R));row=[];r=0;}
}
var classPrefix=this[c9j][o6R],className=classPrefix+(C7R+J3+N73);if(this[c9j][a6j]){className+=' weekNumber';}
var underMin=minDate>new Date(Date[e3y](year,month-1,1,0,0,0)),overMax=maxDate<new Date(Date[(m5R+j5R+A7R)](year,month+1,1,0,0,0));this[B0][(I1y+z6i.w03+E5y)][(c0+x33)]((g13+R7+w7R)+classPrefix+'-iconLeft')[n43]((b0+T+F43+E6y),underMin?(J7):(z6i.w73+X9j+D63));this[(B0)][(Z4y)][(z6i.X6j+P4j+x33)]((g13+R7+w7R)+classPrefix+'-iconRight')[(c9j+N4)]((g13+d7R+v9j+i1),overMax?'none':'block');return (o5R+J3+q1j+z6i.w13+Q5y+L13+F43+i1y+q0+w2)+className+(r9)+(o5R+J3+r93+z6i.w13+P73+V13+i2R)+this[q6y]()+'</thead>'+'<tbody>'+data[H2j]('')+'</tbody>'+(y9+J3+q1j+z6i.w13+i2R);}
,_htmlMonthHead:function(){var f33="joi",p3j="stDa",a=[],firstDay=this[c9j][(z6i.X6j+P4j+E03+p3j+z73)],i18n=this[c9j][U7],dayName=function(day){var a33="weekdays";day+=firstDay;while(day>=7){day-=7;}
return i18n[a33][day];}
;if(this[c9j][a6j]){a[l6R]((o5R+J3+r93+S6R+J3+r93+i2R));}
for(var i=0;i<7;i++){a[l6R]((o5R+J3+r93+i2R)+dayName(i)+'</th>');}
return a[(f33+z6i.W5j)]('');}
,_htmlWeekOfYear:function(d,m,y){var W93="etDa",date=new Date(y,m,d,0,0,0,0);date[(j03+z6i.x6j+z6i.w03+l43+z6i.w03+z6i.x6j)](date[(K0y+z6i.w03+Z7R+S1y)]()+4-(date[(w6j+W93+z73)]()||7));var oneJan=new Date(y,0,1),weekNum=Math[(c9j+z6i.x6j+O9j)]((((date-oneJan)/86400000)+1)/7);return '<td class="'+this[c9j][o6R]+'-week">'+weekNum+'</td>';}
,_options:function(selector,values,labels){var Y6R='ption',Z5j='pt',W2j="ix";if(!labels){labels=values;}
var select=this[(Y8R+p5j)][(F7+P4j+n7j)][(z6i.X6j+j6j+z6i.V9j)]('select.'+this[c9j][(c9j+z6i.S8j+z6i.S1j+N4+R8R+d5j+z6i.X6j+W2j)]+'-'+selector);select.empty();for(var i=0,ien=values.length;i<ien;i++){select[(z6i.S1j+H1j+z6i.W5j+z6i.V9j)]((o5R+z6i.u83+Z5j+r63+Q5y+R7+b9j+w2)+values[i]+'">'+labels[i]+(y9+z6i.u83+Y6R+i2R));}
}
,_optionSet:function(selector,val){var k5R="unknown",B9='cted',select=this[B0][(p4y+z6i.W5j+z6i.w03+z6i.S1j+P4j+X33+E03)][(z6i.X6j+P4j+z6i.W5j+z6i.V9j)]((q0+K2j+J3+w7R)+this[c9j][(c9j+u2+j03+R8R+E03+S6j+P4j+v73)]+'-'+selector),span=select.parent()[Q3y]('span');select[(k33+Y33)](val);var selected=select[(a8R)]((F6R+U3j+k9R+H8R+q0+z6i.w13+o4j+B9));span[L5j](selected.length!==0?selected[(h7y+v73+z6i.w03)]():this[c9j][(P4j+l1y)][k5R]);}
,_optionsTime:function(select,count,inc){var B8j="_pa",C3="hoursAvailable",S0="assPr",classPrefix=this[c9j][(c9j+z6i.S8j+S0+z6i.x6j+z6i.X6j+P4j+v73)],sel=this[B0][G73][(W5y+z6i.V9j)]((B6+I03+w7R)+classPrefix+'-'+select),start=0,end=count,allowed=this[c9j][C3],render=count===12?function(i){return i;}
:this[(B8j+z6i.V9j)];if(count===12){start=1;end=13;}
for(var i=start;i<end;i+=inc){if(!allowed||$[(P4j+W8R+E03+E03+i43)](i,allowed)!==-1){sel[(z6i.S1j+h2j+h2j+O5j+z6i.V9j)]((o5R+z6i.u83+O2+t43+Q5y+R7+P73+S6+w2)+i+'">'+render(i)+'</option>');}
}
}
,_optionsTitle:function(year,month){var Q9j="mon",R5j="nge",D3y="Ra",j8j="llYea",l5="rRa",w1y="yea",Z2j="tFu",A1R="axDat",g0="inDate",classPrefix=this[c9j][(c9j+z6i.S8j+J93+j03+m13+S6j+P4j+v73)],i18n=this[c9j][U7],min=this[c9j][(p5j+g0)],max=this[c9j][(p5j+A1R+z6i.x6j)],minYear=min?min[Z3y]():null,maxYear=max?max[Z3y]():null,i=minYear!==null?minYear:new Date()[(w6j+z6i.x6j+Z2j+z6i.S8j+z6i.S8j+c0j+z6i.x6j+q13)]()-this[c9j][(w1y+l5+z6i.W5j+K0y)],j=maxYear!==null?maxYear:new Date()[(V9R+p1R+B33+j8j+E03)]()+this[c9j][(z73+z6i.x6j+z6i.S1j+E03+D3y+R5j)];this[t5y]('month',this[(M7j+E03+z6i.S1j+h73+z6i.x6j)](0,11),i18n[(Q9j+z6i.w03+c4j+j03)]);this[t5y]('year',this[(M7j+E03+z6i.S1j+R5j)](i,j));}
,_pad:function(i){return i<10?'0'+i:i;}
,_position:function(){var h5y="crollT",N7R="outerWidth",V33="rHe",u6j="offset",offset=this[B0][Q0][u6j](),container=this[B0][G73],inputHeight=this[(Y8R+p5j)][Q0][J03]();container[(c9j+N4)]({top:offset.top+inputHeight,left:offset[u8y]}
)[(l73+h2j+z6i.x6j+x33+U03)]((F7R+v3));var calHeight=container[(j2+h7y+V33+P4j+u7R)](),calWidth=container[N7R](),scrollTop=$(window)[(j03+h5y+p5)]();if(offset.top+inputHeight+calHeight-scrollTop>$(window).height()){var newTop=offset.top-calHeight;container[(c9j+N4)]('top',newTop<0?0:newTop);}
if(calWidth+offset[(u8y)]>$(window).width()){var newLeft=$(window).width()-calWidth;container[(c9j+j03+j03)]('left',newLeft<0?0:newLeft);}
}
,_range:function(start,end){var a=[];for(var i=start;i<=end;i++){a[(j0R+g7)](i);}
return a;}
,_setCalander:function(){var m7R="CFullYe",F0j="cale";if(this[j03][M43]){this[B0][(F0j+x33+z6i.S1j+E03)].empty()[(m7j+z6i.x6j+x33)](this[(M7j+Q4R+p5j+z6i.S8j+m6R+i2j+z6i.W5j+U1y)](this[j03][M43][(K0y+V4+j5R+m7R+z6i.S1j+E03)](),this[j03][(z6i.V9j+K6y+z6i.S8j+i43)][(K0y+z6i.w03+m5R+t7R+m6R+O8+U1y)]()));}
}
,_setTitle:function(){var V93="Ye",a0j="Full";this[S33]('month',this[j03][(z6i.V9j+C8j+e9j+z73)][A4R]());this[S33]((G13+V0),this[j03][(z6i.V9j+P4j+j03+S8y+i43)][(w6j+z6i.x6j+t1+A7R+a0j+V93+q13)]());}
,_setTime:function(){var F0="getSeconds",A2y="_o",A3='mi',V3='mpm',y03="_hours24To12",I0j="onSe",K93="_op",l1j="urs1",d=this[j03][z6i.V9j],hours=d?d[(w6j+z6i.x6j+t1+A7R+Y9R+i2j+E5R+j03)]():0;if(this[j03][(L1y)][(L9R+l1j+d4y)]){this[(K93+I1y+I0j+z6i.w03)]((r93+z6i.u83+P3+V0+q0),this[y03](hours));this[S33]((P73+V3),hours<12?(P73+W43):'pm');}
else{this[S33]('hours',hours);}
this[S33]((A3+t43+L83+l2),d?d[(K0y+Y4+W63+z6i.x6j+j03)]():0);this[(A2y+h2j+z6i.w03+P4j+i2j+z6i.W5j+p5R+z6i.x6j+z6i.w03)]('seconds',d?d[F0]():0);}
,_show:function(){var l='y_C',E8R='TE_Bod',X4="_po",Q73='oll',W8y='sc',W3y="tion",N8="osi",that=this,namespace=this[j03][w0y];this[(r2y+N8+W3y)]();$(window)[(i2j+z6i.W5j)]((W8y+V0+Q73+w7R)+namespace+' resize.'+namespace,function(){that[(X4+j03+P4j+I1y+O8)]();}
);$((V13+Z5+w7R+J3j+E8R+l+k9R+J3+H5+J3))[(i2j+z6i.W5j)]((W8y+V0+z6i.u83+F43+F43+w7R)+namespace,function(){that[(X4+j03+P4j+z6i.w03+P4j+O8)]();}
);$(document)[(i2j+z6i.W5j)]((D63+z6i.w13+i1+x1j+t43+w7R)+namespace,function(e){var C5="yC";if(e[(Z8+C5+w5R)]===9||e[(E8j+z6i.x6j+a4+z6i.x6j)]===27||e[(u43)]===13){that[(M7j+c4j+J7j+z6i.x6j)]();}
}
);setTimeout(function(){$('body')[(O8)]((L13+F43+D6+w7R)+namespace,function(e){var m2="_hi",G1y="lte",parents=$(e[d5y])[(s1y+E03+O5j+z6i.w03+j03)]();if(!parents[(c0+G1y+E03)](that[(z6i.V9j+i2j+p5j)][G73]).length&&e[(D0y+A2j+A33)]!==that[B0][(e4j+z6i.w03)][0]){that[(m2+z6i.V9j+z6i.x6j)]();}
}
);}
,10);}
,_writeOutput:function(focus){var t6="getUTCDate",D5="Mo",c7R="mat",k4="momentLocale",l6j="utc",date=this[j03][z6i.V9j],out=window[(p5j+i2j+z6i.b2R+z6i.W5j+z6i.w03)]?window[I8y][(l6j)](date,undefined,this[c9j][k4],this[c9j][U2])[(u8R+p5j+X93)](this[c9j][(c7+E03+c7R)]):date[h6R]()+'-'+this[(M7j+s1y+z6i.V9j)](date[(K0y+z6i.w03+l33+A7R+D5+d43+c4j)]()+1)+'-'+this[(M7j+s1y+z6i.V9j)](date[t6]());this[(Y8R+p5j)][(Q0)][s73](out);if(focus){this[(z6i.V9j+i2j+p5j)][(Q0)][g33]();}
}
}
);Editor[(Z7R+S1y+k8j+z6i.b2R)][(k4y+z6i.W5j+g4+z6i.S1j+z6i.W5j+X7y)]=0;Editor[W0][(J5R+z6i.S1j+B33+z6i.S8j+z6i.w03+j03)]={classPrefix:(z6i.w13+V13+v8+w6R+C7R+V13+B1y+d0y+F3R),disableDays:null,firstDay:1,format:(u2j+u2j+u2j+u2j+C7R+N9j+N9j+C7R+J3j+J3j),hoursAvailable:null,i18n:Editor[M4y][U7][(z6i.V9j+S1y+S4j)],maxDate:null,minDate:null,minutesIncrement:1,momentStrict:true,momentLocale:'en',onChange:function(){}
,secondsIncrement:1,showWeekNumber:false,yearRange:10}
;(function(){var t0="adMa",O1y="_picker",A73="datetime",O5R="ker",H3R="datepicker",R0R="_preChecked",C7y="radio",D43="checked",k0j=' />',c6R='ast',f7R='inp',L5="Id",a1j="checkbox",q5y="inp",L63="separator",t7="_editor_val",x2y="ipOpts",p33="_addOptions",w8j="_inp",T1y="eId",M5j="af",d3j="att",m9y="password",p3y="_in",i0j="rea",A7y="_val",W4y="dde",k73="prop",L6R="fieldType",r3j='loa',f2j="_enabled",Y0R='oa',Q8="_input",fieldTypes=Editor[t9j];function _buttonText(conf,text){var J4y="uploadText";if(text===null||text===undefined){text=conf[J4y]||"Choose file...";}
conf[Q8][(z6i.X6j+j6j+z6i.V9j)]((V13+Z5+w7R+P3+q6j+Y0R+V13+Q5y+z6i.w73+P3+e6j+z6i.u83+t43))[L5j](text);}
function _commonUpload(editor,conf,dropCallback){var N5R='=',F13='yp',p2='learVa',d6j='red',L1j='nde',k2='oD',I2y='over',t2y='rop',A0R="dragDropText",b5R="dr",k8R="ileR",i63="_ena",s9j='dered',n4j='earValu',p8='ell',l9='il',N3y='ype',G2j='_u',btnClass=editor[(c9j+z6i.S8j+z6i.S1j+j03+s3+j03)][R63][(w8+z6i.w03+V2R)],container=$((o5R+V13+d63+R7+Q5y+L13+F43+i1y+q0+w2+z6i.w13+V13+d63+r1j+V0+G2j+T+K3+r9)+'<div class="eu_table">'+'<div class="row">'+'<div class="cell upload">'+'<button class="'+btnClass+(y0R)+(o5R+d63+m2R+J3+Q5y+J3+N3y+w2+o93+l9+z6i.w13+d2)+(y9+V13+d63+R7+i2R)+(o5R+V13+d63+R7+Q5y+L13+m9R+w2+L13+p8+Q5y+L13+F43+n4j+z6i.w13+r9)+'<button class="'+btnClass+(y0R)+(y9+V13+d63+R7+i2R)+(y9+V13+d63+R7+i2R)+'<div class="row second">'+(o5R+V13+d63+R7+Q5y+L13+m9R+w2+L13+p8+r9)+(o5R+V13+Z5+Q5y+L13+F43+i1y+q0+w2+V13+V0+z6i.u83+T+Y1j+q0+B6y+p0y+V13+d63+R7+i2R)+'</div>'+(o5R+V13+d63+R7+Q5y+L13+F43+P73+s1R+w2+L13+z6i.w13+m5j+r9)+(o5R+V13+d63+R7+Q5y+L13+l7y+q0+w2+V0+H5+s9j+d2)+(y9+V13+d63+R7+i2R)+(y9+V13+d63+R7+i2R)+(y9+V13+Z5+i2R)+(y9+V13+Z5+i2R));conf[Q8]=container;conf[(i63+c9+z6i.x6j+z6i.V9j)]=true;_buttonText(conf);if(window[(p1R+k8R+z6i.x6j+a5j+T03)]&&conf[(b5R+z6i.S1j+w6j+Z7R+E03+p5)]!==false){container[(z6i.X6j+j6j+z6i.V9j)]('div.drop span')[R9y](conf[A0R]||(Z7R+E03+d2j+M2+z6i.S1j+z6i.W5j+z6i.V9j+M2+z6i.V9j+L73+h2j+M2+z6i.S1j+M2+z6i.X6j+P4j+E5y+M2+c4j+T03+z6i.x6j+M2+z6i.w03+i2j+M2+B33+h2j+z6i.S8j+i2j+z6i.S1j+z6i.V9j));var dragDrop=container[a8R]((V13+d63+R7+w7R+V13+t2y));dragDrop[(i2j+z6i.W5j)]((V13+o3y+T),function(e){var D1j="sfer",Z33="Tr",I2="nalEv";if(conf[(u6y+z6i.W5j+z6i.F8j+s4j)]){Editor[G8R](editor,conf,e[(i2j+E03+P4j+w6j+P4j+I2+z6i.x6j+d43)][(z6i.V9j+c7y+Z33+z6i.S1j+z6i.W5j+D1j)][(z6i.X6j+P4j+E5y+j03)],_buttonText,dropCallback);dragDrop[l0j]('over');}
return false;}
)[(O8)]('dragleave dragexit',function(e){if(conf[f2j]){dragDrop[(d5j+p5j+G2+z6i.x6j+o2j+S2y)]((I2y));}
return false;}
)[(O8)]('dragover',function(e){if(conf[(M7j+O5j+z6i.F8j+s4j)]){dragDrop[(z6i.S1j+P1R+t7y+N4)]((I2y));}
return false;}
);editor[(i2j+z6i.W5j)]((z6i.u83+T+z6i.w13+t43),function(){var X8R='_U',j2y='agove';$((G8))[(i2j+z6i.W5j)]((V13+V0+j2y+V0+w7R+J3j+e3+D8j+T+F43+Y0R+V13+Q5y+V13+V0+z6i.u83+T+w7R+J3j+f73+X8R+T+r3j+V13),function(e){return false;}
);}
)[(O8)]('close',function(){var q='pload',L7y='TE_U',N5j='TE_Uplo';$('body')[v03]((V13+V0+P73+I93+z6i.u83+X0y+w7R+J3j+N5j+D8+Q5y+V13+V0+F6R+w7R+J3j+L7y+q));}
);}
else{container[(z6i.S1j+z6i.V9j+M3y+V4y+j03+j03)]((t43+k2+V0+F6R));container[(l73+h2j+O5j+z6i.V9j)](container[(c0+x33)]((V13+Z5+w7R+V0+z6i.w13+L1j+d6j)));}
container[(z6i.X6j+j6j+z6i.V9j)]((g13+R7+w7R+L13+p2+S6+Q5y+z6i.w73+P3+e6j+k9R))[O8]((m4j),function(){Editor[t9j][(Z8R+r5j)][(j03+z6i.x6j+z6i.w03)][(q6R)](editor,conf,'');}
);container[a8R]((d63+z1y+P3+J3+n03+J3+F13+z6i.w13+N5R+o93+d63+o4j+m03))[O8]((L13+I8j+t43+c8R),function(){var m6="upl";Editor[(m6+x1+z6i.V9j)](editor,conf,this[(z6i.X6j+O9j+l03)],_buttonText,function(ids){dropCallback[q6R](editor,ids);container[(z6i.X6j+j6j+z6i.V9j)]('input[type=file]')[s73]('');}
);}
);return container;}
function _triggerChange(input){setTimeout(function(){var Y2R="rig";input[(z6i.w03+Y2R+w6j+z6i.x6j+E03)]((L13+I8j+E3y+z6i.w13),{editor:true,editorSet:true}
);}
,0);}
var baseFieldType=$[n7R](true,{}
,Editor[Z03][L6R],{get:function(conf){return conf[(k4y+F2j)][s73]();}
,set:function(conf,val){conf[(M7j+P4j+Q63+B33+z6i.w03)][(k33+z6i.S1j+z6i.S8j)](val);_triggerChange(conf[(k4y+Q63+B33+z6i.w03)]);}
,enable:function(conf){conf[Q8][(h2j+E03+p5)]('disabled',false);}
,disable:function(conf){var s4y='sa';conf[(M7j+P4j+Q63+B33+z6i.w03)][(k73)]((g13+s4y+z6i.w73+o4j+V13),true);}
,canReturnSubmit:function(conf,node){return true;}
}
);fieldTypes[(c4j+P4j+W4y+z6i.W5j)]={create:function(conf){var D33="value";conf[(A7y)]=conf[D33];return null;}
,get:function(conf){return conf[A7y];}
,set:function(conf,val){conf[A7y]=val;}
}
;fieldTypes[(i0j+z6i.V9j+i2j+z6i.W5j+G9R)]=$[n7R](true,{}
,baseFieldType,{create:function(conf){var F4y='don';conf[Q8]=$('<input/>')[G2y]($[n7R]({id:Editor[h3R](conf[(P4j+z6i.V9j)]),type:'text',readonly:(r8+P73+F4y+F43+i1)}
,conf[(X93+z6i.w03+E03)]||{}
));return conf[(p3y+h2j+B33+z6i.w03)][0];}
}
);fieldTypes[(R9y)]=$[(z6i.x6j+C9y+z6i.x6j+x33)](true,{}
,baseFieldType,{create:function(conf){conf[Q8]=$('<input/>')[G2y]($[n7R]({id:Editor[h3R](conf[(P4j+z6i.V9j)]),type:'text'}
,conf[G2y]||{}
));return conf[Q8][0];}
}
);fieldTypes[m9y]=$[(p13+z6i.w03+O5j+z6i.V9j)](true,{}
,baseFieldType,{create:function(conf){var C2y='wo',C2R='pas';conf[(k4y+Q63+B33+z6i.w03)]=$('<input/>')[(d3j+E03)]($[(p13+h7y+z6i.W5j+z6i.V9j)]({id:Editor[h3R](conf[J7j]),type:(C2R+q0+C2y+V0+V13)}
,conf[(z6i.S1j+z6i.w03+z6i.w03+E03)]||{}
));return conf[(k4y+z6i.W5j+h2j+B33+z6i.w03)][0];}
}
);fieldTypes[(z6i.w03+z6i.x6j+C9y+z6i.S1j+i0j)]=$[(p13+z6i.w03+z6i.x6j+z6i.W5j+z6i.V9j)](true,{}
,baseFieldType,{create:function(conf){var f4j='ext';conf[Q8]=$((o5R+J3+f4j+N7y+p9+q4))[(z6i.S1j+z6i.w03+l4y)]($[(z6i.x6j+C9y+z6i.x6j+z6i.W5j+z6i.V9j)]({id:Editor[(j03+M5j+T1y)](conf[(P4j+z6i.V9j)])}
,conf[(z6i.S1j+j8y+E03)]||{}
));return conf[(w8j+K2R)][0];}
,canReturnSubmit:function(conf,node){return false;}
}
);fieldTypes[K9]=$[(p13+s13)](true,{}
,baseFieldType,{_addOptions:function(conf,opts,append){var v5y="optionsPair",A5y="r_v",q93="hidden",x0j="placeholderDisabled",o73="older",M5="rValue",z6y="ceh",y1="olderVal",l9j="placeh",elOpts=conf[(M7j+P4j+c3+z6i.w03)][0][(i2j+U0R+L2R+j03)],countOffset=0;if(!append){elOpts.length=0;if(conf[(S8y+z6i.S1j+X7y+c4j+i2j+z6i.S8j+z6i.V9j+T03)]!==undefined){var placeholderValue=conf[(l9j+y1+B33+z6i.x6j)]!==undefined?conf[(S8y+z6i.S1j+z6y+i2j+z6i.S8j+C1R+M5)]:'';countOffset+=1;elOpts[0]=new Option(conf[(R03+z6i.x6j+c4j+o73)],placeholderValue);var disabled=conf[x0j]!==undefined?conf[x0j]:true;elOpts[0][q93]=disabled;elOpts[0][D5j]=disabled;elOpts[0][(M7j+Z6j+o4R+A5y+z6i.S1j+z6i.S8j)]=placeholderValue;}
}
else{countOffset=elOpts.length;}
if(opts){Editor[(s1y+P4j+c13)](opts,conf[v5y],function(val,label,i,attr){var option=new Option(label,val);option[(M7j+z6i.x6j+x6R+z6i.w03+i2j+P6j+k33+z6i.S1j+z6i.S8j)]=val;if(attr){$(option)[(d3j+E03)](attr);}
elOpts[i+countOffset]=option;}
);}
}
,create:function(conf){var n4R="ions",j9j="multipl",s9R="eI";conf[(k4y+c3+z6i.w03)]=$((o5R+q0+z6i.w13+F43+z6i.w13+z6i.U4j+q4))[(z6i.S1j+j8y+E03)]($[(z6i.x6j+v73+h7y+x33)]({id:Editor[(j03+z6i.S1j+z6i.X6j+s9R+z6i.V9j)](conf[(P4j+z6i.V9j)]),multiple:conf[(j9j+z6i.x6j)]===true}
,conf[G2y]||{}
))[O8]('change.dte',function(e,d){var T1="stS";if(!d||!d[(Z6j+G8j+S5)]){conf[(G8y+z6i.S1j+T1+z6i.x6j+z6i.w03)]=fieldTypes[(j03+t8j+z6i.x6j+c9j+z6i.w03)][(w6j+A33)](conf);}
}
);fieldTypes[K9][p33](conf,conf[(i2j+h2j+z6i.w03+n4R)]||conf[x2y]);return conf[(M7j+P4j+z6i.W5j+h2j+K2R)][0];}
,update:function(conf,options,append){var D4="astSe",e2y="_add";fieldTypes[(s3+E5y+c9j+z6i.w03)][(e2y+s4R+U0R+P4j+i2j+f63)](conf,options,append);var lastSet=conf[(G8y+D4+z6i.w03)];if(lastSet!==undefined){fieldTypes[(j03+t8j+G9j+z6i.w03)][(R2j)](conf,lastSet,true);}
_triggerChange(conf[(k4y+F2j)]);}
,get:function(conf){var B4R="ator",P1="epar",q9j="multiple",q8='elect',val=conf[Q8][a8R]((z6i.u83+O2+t43+H8R+q0+q8+z6i.w13+V13))[(p5j+l73)](function(){return this[t7];}
)[(z6i.w03+i2j+c1y+i43)]();if(conf[q9j]){return conf[(j03+P1+z6i.S1j+c3j)]?val[(M4j+i2j+P4j+z6i.W5j)](conf[(s3+h2j+z6i.S1j+E03+B4R)]):val;}
return val.length?val[0]:null;}
,set:function(conf,val,localUpdate){var P2="ted",u4="ltip",g5="_lastSet";if(!localUpdate){conf[g5]=val;}
if(conf[(y6j+z6i.S8j+I1y+S8y+z6i.x6j)]&&conf[L63]&&!$[(C8j+C3R+B13+z6i.S1j+z73)](val)){val=typeof val===(h1R+V0+j6+I93)?val[(e6+z6i.S8j+G8j)](conf[L63]):[];}
else if(!$[p03](val)){val=[val];}
var i,len=val.length,found,allFound=false,options=conf[(M7j+q5y+K2R)][a8R]('option');conf[Q8][(c0+x33)]('option')[w4j](function(){found=false;for(i=0;i<len;i++){if(this[t7]==val[i]){found=true;allFound=true;break;}
}
this[(j03+v6y+z6i.w03+z6i.x6j+z6i.V9j)]=found;}
);if(conf[(R03+z6i.x6j+c4j+x8+C1R+E03)]&&!allFound&&!conf[(y6j+u4+E5y)]&&options.length){options[0][(j03+z6i.x6j+z6i.S8j+z6i.x6j+c9j+P2)]=true;}
if(!localUpdate){_triggerChange(conf[Q8]);}
return allFound;}
,destroy:function(conf){var K83='ange';conf[Q8][(i2j+z6i.X6j+z6i.X6j)]((A3j+K83+w7R+V13+J3+z6i.w13));}
}
);fieldTypes[a1j]=$[(z6i.x6j+c33+z6i.V9j)](true,{}
,baseFieldType,{_addOptions:function(conf,opts,append){var val,label,jqInput=conf[(p3y+h2j+K2R)],offset=0;if(!append){jqInput.empty();}
else{offset=$('input',jqInput).length;}
if(opts){Editor[(h2j+z6i.S1j+K8j+j03)](opts,conf[(i2j+h2j+z6i.w03+L2R+j03+R8R+A03+E03)],function(val,label,i,attr){var d8R="ttr",f5j='pu';jqInput[o6y]((o5R+V13+d63+R7+i2R)+(o5R+d63+t43+f5j+J3+Q5y+d63+V13+w2)+Editor[h3R](conf[(J7j)])+'_'+(i+offset)+'" type="checkbox" />'+(o5R+F43+P73+z6i.w73+I8+Q5y+o93+z6i.u83+V0+w2)+Editor[(j03+z6i.S1j+z6i.X6j+z6i.x6j+L5)](conf[J7j])+'_'+(i+offset)+'">'+label+(y9+F43+Q1y+i2R)+(y9+V13+d63+R7+i2R));$('input:last',jqInput)[(z6i.S1j+d8R)]((s2+I33),val)[0][t7]=val;if(attr){$((f7R+L83+H8R+F43+c6R),jqInput)[G2y](attr);}
}
);}
}
,create:function(conf){conf[Q8]=$((o5R+V13+Z5+k0j));fieldTypes[a1j][(M7j+z6i.S1j+P1R+s4R+O63+j03)](conf,conf[K0R]||conf[x2y]);return conf[(k4y+F2j)][0];}
,get:function(conf){var o5j="ara",k7j="unselectedValue",h0y='hecked',out=[],selected=conf[(M7j+P4j+z6i.W5j+h2j+K2R)][a8R]((F+H8R+L13+h0y));if(selected.length){selected[(w4j)](function(){var e8="r_va";out[(h2j+B33+j03+c4j)](this[(u6y+z6i.V9j+G8j+i2j+e8+z6i.S8j)]);}
);}
else if(conf[k7j]!==undefined){out[l6R](conf[(B33+z6i.W5j+s3+z6i.S8j+G9j+h7y+z6i.V9j+c2R+z6i.S1j+z6i.S8j+r7R)]);}
return conf[L63]===undefined||conf[L63]===null?out:out[(H2j)](conf[(j03+v2j+o5j+z6i.w03+S5)]);}
,set:function(conf,val){var jqInputs=conf[(M7j+P4j+F2j)][a8R]((F));if(!$[(j0y+E03+Z4j+z73)](val)&&typeof val===(q0+z9j+j6+I93)){val=val[G3R](conf[(j03+z6i.x6j+h2j+q13+z6i.S1j+c3j)]||'|');}
else if(!$[(P4j+j03+S5y+E03+z6i.S1j+z73)](val)){val=[val];}
var i,len=val.length,found;jqInputs[(z6i.x6j+z6i.S1j+b1y)](function(){var O3R="_v";found=false;for(i=0;i<len;i++){if(this[(u6y+z6i.V9j+P4j+z6i.w03+S5+O3R+z6i.S1j+z6i.S8j)]==val[i]){found=true;break;}
}
this[D43]=found;}
);_triggerChange(jqInputs);}
,enable:function(conf){conf[(M7j+e4j+z6i.w03)][a8R]('input')[(N+h2j)]((V13+d8+P73+z6i.w73+F43+u6),false);}
,disable:function(conf){conf[(M7j+j6j+h2j+K2R)][a8R]((d63+z1y+L83))[(N2y+i2j+h2j)]('disabled',true);}
,update:function(conf,options,append){var h4="kb",checkbox=fieldTypes[(c9j+c4j+G9j+h4+i2j+v73)],currVal=checkbox[(K0y+z6i.w03)](conf);checkbox[p33](conf,options,append);checkbox[(j03+A33)](conf,currVal);}
}
);fieldTypes[C7y]=$[(z6i.x6j+C9y+O5j+z6i.V9j)](true,{}
,baseFieldType,{_addOptions:function(conf,opts,append){var v3j="pti",val,label,jqInput=conf[Q8],offset=0;if(!append){jqInput.empty();}
else{offset=$('input',jqInput).length;}
if(opts){Editor[(o0y+c13)](opts,conf[(i2j+v3j+i2j+z6i.W5j+j03+R8R+A03+E03)],function(val,label,i,attr){var b0j="_edit",N33="am";jqInput[o6y]((o5R+V13+d63+R7+i2R)+'<input id="'+Editor[h3R](conf[(J7j)])+'_'+(i+offset)+'" type="radio" name="'+conf[(z6i.W5j+N33+z6i.x6j)]+(y0R)+'<label for="'+Editor[(j03+M5j+T1y)](conf[(J7j)])+'_'+(i+offset)+(r9)+label+(y9+F43+t4+I8+i2R)+'</div>');$('input:last',jqInput)[(z6i.S1j+j8y+E03)]((R7+P73+F43+I33),val)[0][(b0j+S5+M7j+n1j+z6i.S8j)]=val;if(attr){$((d63+z1y+P3+J3+H8R+F43+c6R),jqInput)[G2y](attr);}
}
);}
}
,create:function(conf){var f8="pO";conf[Q8]=$((o5R+V13+d63+R7+k0j));fieldTypes[C7y][p33](conf,conf[(p5+z6i.w03+P4j+i2j+f63)]||conf[(P4j+f8+h2j+z6i.o8y)]);this[O8]('open',function(){conf[(M7j+P4j+c3+z6i.w03)][a8R]('input')[(z6i.x6j+a6y)](function(){if(this[R0R]){this[(b1y+J1j+z6i.x6j+z6i.V9j)]=true;}
}
);}
);return conf[Q8][0];}
,get:function(conf){var el=conf[(M7j+e4j+z6i.w03)][(c0+x33)]((d63+z1y+L83+H8R+L13+r93+z6i.w13+Z7j+u6));return el.length?el[0][t7]:undefined;}
,set:function(conf,val){var that=this;conf[Q8][a8R]('input')[w4j](function(){var N4j="eCheck",O4y="ecke",v7j="or_v",t3R="_ed",O9R="cked";this[(M7j+h2j+E03+z6i.x6j+A7R+K3R+O9R)]=false;if(this[(t3R+G8j+v7j+z6i.S1j+z6i.S8j)]==val){this[D43]=true;this[R0R]=true;}
else{this[(b1y+O4y+z6i.V9j)]=false;this[(M7j+h2j+E03+N4j+Z6j)]=false;}
}
);_triggerChange(conf[(w8j+K2R)][(W5y+z6i.V9j)]((f7R+L83+H8R+L13+r93+q9+b9R+V13)));}
,enable:function(conf){conf[Q8][(z6i.X6j+P4j+x33)]((j6+s9))[(k73)]((g13+q0+q1j+z6i.w13+V13),false);}
,disable:function(conf){conf[(w8j+K2R)][a8R]((d63+t43+T+L83))[(k73)]('disabled',true);}
,update:function(conf,options,append){var X1="ddOp",S5R="dio",radio=fieldTypes[(Z4j+S5R)],currVal=radio[V9R](conf);radio[(M7j+z6i.S1j+X1+I1y+p2j)](conf,options,append);var inputs=conf[(M7j+P4j+Q63+B33+z6i.w03)][a8R]((d63+m2R+J3));radio[(j03+A33)](conf,inputs[(c0+K1R+T03)]((n03+R7+P73+S6+w2)+currVal+(X6y)).length?currVal:inputs[(Q03)](0)[G2y]((R7+U0y+P3+z6i.w13)));}
}
);fieldTypes[Z1y]=$[(r7j+z6i.x6j+z6i.W5j+z6i.V9j)](true,{}
,baseFieldType,{create:function(conf){var v6='typ',J1R="RFC_2822",b4="dateFormat",C93="eFo",Q6j='yui',p0='q',e4y="dCla";conf[(p3y+h2j+K2R)]=$((o5R+d63+m2R+J3+k0j))[(d3j+E03)]($[n7R]({id:Editor[h3R](conf[(P4j+z6i.V9j)]),type:(J3+R7y+J3)}
,conf[(z6i.S1j+z6i.w03+l4y)]));if($[H3R]){conf[(k4y+z6i.W5j+j0R+z6i.w03)][(a5j+e4y+j03+j03)]((z6i.b63+p0+P3+z6i.w13+V0+Q6j));if(!conf[(z6i.V9j+X93+C93+E03+p5j+X93)]){conf[b4]=$[H3R][J1R];}
setTimeout(function(){var Z6y="dateImage",b8y="both",I3R="_inpu";$(conf[(I3R+z6i.w03)])[H3R]($[n7R]({showOn:(b8y),dateFormat:conf[b4],buttonImage:conf[Z6y],buttonImageOnly:true,onSelect:function(){var L7j="lick";conf[Q8][g33]()[(c9j+L7j)]();}
}
,conf[s1]));$('#ui-datepicker-div')[n43]('display','none');}
,10);}
else{conf[(M7j+P4j+z6i.W5j+j0R+z6i.w03)][(z6i.S1j+j8y+E03)]((v6+z6i.w13),'date');}
return conf[(M7j+q5y+K2R)][0];}
,set:function(conf,val){if($[H3R]&&conf[Q8][F3j]('hasDatepicker')){conf[Q8][H3R]((j03+A33+K2+z6i.x6j),val)[R83]();}
else{$(conf[(M7j+P4j+z6i.W5j+E6j)])[(s73)](val);}
}
,enable:function(conf){var y0j='isab',K5j="pic";if($[(z6i.V9j+z6i.S1j+h7y+K5j+O5R)]){conf[(k4y+z6i.W5j+h2j+B33+z6i.w03)][H3R]((z6i.x6j+z6i.W5j+z6i.S1j+i9j+E5y));}
else{$(conf[Q8])[k73]((V13+y0j+o4j+V13),false);}
}
,disable:function(conf){if($[H3R]){conf[(k4y+z6i.W5j+j0R+z6i.w03)][H3R]((x6R+j03+z6i.F8j+E5y));}
else{$(conf[Q8])[k73]('disabled',true);}
}
,owns:function(conf,node){var L3j='tep';return $(node)[(s1y+E03+P9+j03)]('div.ui-datepicker').length||$(node)[(h2j+z6i.S1j+d5j+z6i.W5j+z6i.o8y)]((g13+R7+w7R+P3+d63+C7R+V13+P73+L3j+r3+D63+X2+C7R+r93+p9+V13+z6i.w13+V0)).length?true:false;}
}
);fieldTypes[A73]=$[n7R](true,{}
,baseFieldType,{create:function(conf){var U5="_closeFn",p8j="forma",j7j='xt',n83="fe";conf[Q8]=$((o5R+d63+z1y+L83+k0j))[G2y]($[(z6i.x6j+v73+q3+z6i.V9j)](true,{id:Editor[(V+n83+L5)](conf[(J7j)]),type:(w2R+j7j)}
,conf[(d3j+E03)]));conf[O1y]=new Editor[(l43+z6i.w03+z6i.x6j+j5R+P4j+p5j+z6i.x6j)](conf[Q8],$[n7R]({format:conf[(p8j+z6i.w03)],i18n:this[(U7)][(z6i.V9j+X93+z6i.x6j+z6i.w03+P4j+p5j+z6i.x6j)],onChange:function(){_triggerChange(conf[(M7j+P4j+F2j)]);}
}
,conf[(p5+z6i.o8y)]));conf[(M7j+z2j+T1R+z6i.W5j)]=function(){var f43="hide",X9R="_picke";conf[(X9R+E03)][f43]();}
;this[(i2j+z6i.W5j)]((L13+F43+z6i.u83+V5y),conf[U5]);return conf[(p3y+h2j+K2R)][0];}
,set:function(conf,val){conf[(M7j+h2j+P4j+B9y+z6i.x6j+E03)][(k33+Y33)](val);_triggerChange(conf[(k4y+z6i.W5j+j0R+z6i.w03)]);}
,owns:function(conf,node){var r4R="owns",p3R="picker";return conf[(M7j+p3R)][r4R](node);}
,errorMessage:function(conf,msg){var H6y="orMsg";conf[(M7j+g4y+B9y+z6i.x6j+E03)][(z6i.x6j+B13+H6y)](msg);}
,destroy:function(conf){var F3y="oy",O8j="estr";this[(R6+z6i.X6j)]((q7j+z6i.u83+V5y),conf[(M7j+c9j+d3R+j03+z6i.x6j+i6R)]);conf[O1y][(z6i.V9j+O8j+F3y)]();}
,minDate:function(conf,min){var N7="min",t0R="cker";conf[(r2y+P4j+t0R)][(N7)](min);}
,maxDate:function(conf,max){var L8="_pic";conf[(L8+O5R)][(r8R+v73)](max);}
}
);fieldTypes[(B33+h2j+z6i.S8j+x1+z6i.V9j)]=$[n7R](true,{}
,baseFieldType,{create:function(conf){var editor=this,container=_commonUpload(editor,conf,function(val){var Y6="dTypes";Editor[(z6i.X6j+P7j+z6i.S8j+Y6)][G8R][(s3+z6i.w03)][(b3y+z6i.S8j+z6i.S8j)](editor,conf,val[0]);}
);return container;}
,get:function(conf){return conf[A7y];}
,set:function(conf,val){var A7j="dler",g1="Han",y6y="rigge",j4y="clearText",A7="clearTex",K8R="ileT",C7j="noF";conf[A7y]=val;var container=conf[(M7j+j6j+h2j+B33+z6i.w03)];if(conf[M43]){var rendered=container[(c0+z6i.W5j+z6i.V9j)]('div.rendered');if(conf[(M7j+n1j+z6i.S8j)]){rendered[L5j](conf[(z6i.V9j+K6y+z6i.S8j+z6i.S1j+z73)](conf[A7y]));}
else{rendered.empty()[o6y]('<span>'+(conf[(C7j+K8R+z6i.x6j+v73+z6i.w03)]||(F6j+z6i.u83+Q5y+o93+d63+o4j))+'</span>');}
}
var button=container[a8R]('div.clearValue button');if(val&&conf[(A7+z6i.w03)]){button[L5j](conf[j4y]);container[l0j]('noClear');}
else{container[A4y]('noClear');}
conf[(k4y+Q63+B33+z6i.w03)][(c0+z6i.W5j+z6i.V9j)]('input')[(z6i.w03+y6y+E03+g1+A7j)]((P3+T+r3j+V13+w7R+z6i.w13+V13+u5+V0),[conf[A7y]]);}
,enable:function(conf){var s7='sab';conf[(k4y+z6i.W5j+h2j+B33+z6i.w03)][a8R]('input')[k73]((g13+s7+o4j+V13),false);conf[f2j]=true;}
,disable:function(conf){var W4j="bled",M4R='isa';conf[(M7j+P4j+c3+z6i.w03)][(W5y+z6i.V9j)]((d63+t43+T+P3+J3))[(h2j+E03+i2j+h2j)]((V13+M4R+z6i.w73+o4j+V13),true);conf[(u6y+z6i.W5j+z6i.S1j+W4j)]=false;}
,canReturnSubmit:function(conf,node){return false;}
}
);fieldTypes[(B33+h2j+z6i.S8j+i2j+t0+z6i.W5j+z73)]=$[n7R](true,{}
,baseFieldType,{create:function(conf){var x5='tto',a7R='mul',s8="uploadMany",editor=this,container=_commonUpload(editor,conf,function(val){var z5="ypes";var G5R="fiel";conf[A7y]=conf[(M7j+k33+Y33)][R4y](val);Editor[(G5R+H8y+z5)][s8][(s3+z6i.w03)][q6R](editor,conf,conf[A7y]);}
);container[(z6i.S1j+P1R+A7R+V4y+j03+j03)]((a7R+J3+d63))[(i2j+z6i.W5j)]((L13+v8j+L13+D63),(z6i.w73+P3+x5+t43+w7R+V0+J5+z6i.u83+R7+z6i.w13),function(e){var s7j="cal",t="gation",M03="rop";e[(j03+V0j+R8R+M03+z6i.S1j+t)]();var idx=$(this).data((d63+V13+X7));conf[(M7j+k33+z6i.S1j+z6i.S8j)][D2R](idx,1);Editor[(z6i.X6j+P4j+z6i.x6j+O8y+j5R+z73+h2j+z6i.x6j+j03)][s8][R2j][(s7j+z6i.S8j)](editor,conf,conf[(M7j+s73)]);}
);return container;}
,get:function(conf){return conf[(M7j+k33+Y33)];}
,set:function(conf,val){var b73="noFileText",F33='rray',J6='ctio',g8j='lle',R4j="sA";if(!val){val=[];}
if(!$[(P4j+R4j+E03+E03+i43)](val)){throw (M0R+F43+Y0R+V13+Q5y+L13+z6i.u83+g8j+J6+t43+q0+Q5y+W43+P3+h1R+Q5y+r93+P73+R7+z6i.w13+Q5y+P73+t43+Q5y+P73+F33+Q5y+P73+q0+Q5y+P73+Q5y+R7+U0y+P3+z6i.w13);}
conf[A7y]=val;var that=this,container=conf[(p3y+E6j)];if(conf[M43]){var rendered=container[a8R]((V13+d63+R7+w7R+V0+z6i.w13+t43+J73+r8+V13)).empty();if(val.length){var list=$((o5R+P3+F43+q4))[(o6y+j5R+i2j)](rendered);$[(z6i.x6j+a6y)](val,function(i,file){var m5y='emo',Q2R=' <';list[o6y]((o5R+F43+d63+i2R)+conf[(x13+S8y+i43)](file,i)+(Q2R+z6i.w73+P3+J3+J3+k9R+Q5y+L13+v9j+s1R+w2)+that[w0][(c7+E03+p5j)][d13]+(Q5y+V0+m5y+j9+y73+V13+P73+J3+P73+C7R+d63+V13+X7+w2)+i+'">&times;</button>'+'</li>');}
);}
else{rendered[o6y]((o5R+q0+B6y+i2R)+(conf[b73]||'No files')+'</span>');}
}
conf[Q8][a8R]('input')[K3j]('upload.editor',[conf[A7y]]);}
,enable:function(conf){conf[(M7j+P4j+z6i.W5j+h2j+B33+z6i.w03)][a8R]((d63+t43+T+L83))[k73]('disabled',false);conf[f2j]=true;}
,disable:function(conf){conf[Q8][a8R]('input')[k73]('disabled',true);conf[f2j]=false;}
,canReturnSubmit:function(conf,node){return false;}
}
);}
());if(DataTable[r7j][(z6i.x6j+z6i.V9j+P4j+c3j+V6y+e13)]){$[(Z9R+x33)](Editor[(R9+O8y+I13+h2j+z6i.x6j+j03)],DataTable[r7j][(z6i.x6j+z6i.V9j+P4j+z6i.w03+F9j+z6i.x6j+O8y+j03)]);}
DataTable[(z6i.x6j+C9y)][(k8y+D0R)]=Editor[(z6i.X6j+P4j+z6i.x6j+O3j+z73+h2j+l03)];Editor[(z6i.X6j+P4j+z6i.S8j+z6i.x6j+j03)]={}
;Editor.prototype.CLASS="Editor";Editor[(k33+Q3+P4j+O8)]=(M6y+b9y+x5y+b9y+d4y);return Editor;}
));

/*! Buttons for DataTables 1.5.1
 * ©2016-2017 SpryMedia Ltd - datatables.net/license
 */

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


// Used for namespacing events added to the document by each instance, so they
// can be removed on destroy
var _instCounter = 0;

// Button namespacing counter for namespacing events on individual buttons
var _buttonCounter = 0;

var _dtButtons = DataTable.ext.buttons;

/**
 * [Buttons description]
 * @param {[type]}
 * @param {[type]}
 */
var Buttons = function( dt, config )
{
	// If there is no config set it to an empty object
	if ( typeof( config ) === 'undefined' ) {
		config = {};	
	}
	
	// Allow a boolean true for defaults
	if ( config === true ) {
		config = {};
	}

	// For easy configuration of buttons an array can be given
	if ( $.isArray( config ) ) {
		config = { buttons: config };
	}

	this.c = $.extend( true, {}, Buttons.defaults, config );

	// Don't want a deep copy for the buttons
	if ( config.buttons ) {
		this.c.buttons = config.buttons;
	}

	this.s = {
		dt: new DataTable.Api( dt ),
		buttons: [],
		listenKeys: '',
		namespace: 'dtb'+(_instCounter++)
	};

	this.dom = {
		container: $('<'+this.c.dom.container.tag+'/>')
			.addClass( this.c.dom.container.className )
	};

	this._constructor();
};


$.extend( Buttons.prototype, {
	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Public methods
	 */

	/**
	 * Get the action of a button
	 * @param  {int|string} Button index
	 * @return {function}
	 *//**
	 * Set the action of a button
	 * @param  {node} node Button element
	 * @param  {function} action Function to set
	 * @return {Buttons} Self for chaining
	 */
	action: function ( node, action )
	{
		var button = this._nodeToButton( node );

		if ( action === undefined ) {
			return button.conf.action;
		}

		button.conf.action = action;

		return this;
	},

	/**
	 * Add an active class to the button to make to look active or get current
	 * active state.
	 * @param  {node} node Button element
	 * @param  {boolean} [flag] Enable / disable flag
	 * @return {Buttons} Self for chaining or boolean for getter
	 */
	active: function ( node, flag ) {
		var button = this._nodeToButton( node );
		var klass = this.c.dom.button.active;
		var jqNode = $(button.node);

		if ( flag === undefined ) {
			return jqNode.hasClass( klass );
		}

		jqNode.toggleClass( klass, flag === undefined ? true : flag );

		return this;
	},

	/**
	 * Add a new button
	 * @param {object} config Button configuration object, base string name or function
	 * @param {int|string} [idx] Button index for where to insert the button
	 * @return {Buttons} Self for chaining
	 */
	add: function ( config, idx )
	{
		var buttons = this.s.buttons;

		if ( typeof idx === 'string' ) {
			var split = idx.split('-');
			var base = this.s;

			for ( var i=0, ien=split.length-1 ; i<ien ; i++ ) {
				base = base.buttons[ split[i]*1 ];
			}

			buttons = base.buttons;
			idx = split[ split.length-1 ]*1;
		}

		this._expandButton( buttons, config, false, idx );
		this._draw();

		return this;
	},

	/**
	 * Get the container node for the buttons
	 * @return {jQuery} Buttons node
	 */
	container: function ()
	{
		return this.dom.container;
	},

	/**
	 * Disable a button
	 * @param  {node} node Button node
	 * @return {Buttons} Self for chaining
	 */
	disable: function ( node ) {
		var button = this._nodeToButton( node );

		$(button.node).addClass( this.c.dom.button.disabled );

		return this;
	},

	/**
	 * Destroy the instance, cleaning up event handlers and removing DOM
	 * elements
	 * @return {Buttons} Self for chaining
	 */
	destroy: function ()
	{
		// Key event listener
		$('body').off( 'keyup.'+this.s.namespace );

		// Individual button destroy (so they can remove their own events if
		// needed). Take a copy as the array is modified by `remove`
		var buttons = this.s.buttons.slice();
		var i, ien;
		
		for ( i=0, ien=buttons.length ; i<ien ; i++ ) {
			this.remove( buttons[i].node );
		}

		// Container
		this.dom.container.remove();

		// Remove from the settings object collection
		var buttonInsts = this.s.dt.settings()[0];

		for ( i=0, ien=buttonInsts.length ; i<ien ; i++ ) {
			if ( buttonInsts.inst === this ) {
				buttonInsts.splice( i, 1 );
				break;
			}
		}

		return this;
	},

	/**
	 * Enable / disable a button
	 * @param  {node} node Button node
	 * @param  {boolean} [flag=true] Enable / disable flag
	 * @return {Buttons} Self for chaining
	 */
	enable: function ( node, flag )
	{
		if ( flag === false ) {
			return this.disable( node );
		}

		var button = this._nodeToButton( node );
		$(button.node).removeClass( this.c.dom.button.disabled );

		return this;
	},

	/**
	 * Get the instance name for the button set selector
	 * @return {string} Instance name
	 */
	name: function ()
	{
		return this.c.name;
	},

	/**
	 * Get a button's node
	 * @param  {node} node Button node
	 * @return {jQuery} Button element
	 */
	node: function ( node )
	{
		var button = this._nodeToButton( node );
		return $(button.node);
	},

	/**
	 * Set / get a processing class on the selected button
	 * @param  {boolean} flag true to add, false to remove, undefined to get
	 * @return {boolean|Buttons} Getter value or this if a setter.
	 */
	processing: function ( node, flag )
	{
		var button = this._nodeToButton( node );

		if ( flag === undefined ) {
			return $(button.node).hasClass( 'processing' );
		}

		$(button.node).toggleClass( 'processing', flag );

		return this;
	},

	/**
	 * Remove a button.
	 * @param  {node} node Button node
	 * @return {Buttons} Self for chaining
	 */
	remove: function ( node )
	{
		var button = this._nodeToButton( node );
		var host = this._nodeToHost( node );
		var dt = this.s.dt;

		// Remove any child buttons first
		if ( button.buttons.length ) {
			for ( var i=button.buttons.length-1 ; i>=0 ; i-- ) {
				this.remove( button.buttons[i].node );
			}
		}

		// Allow the button to remove event handlers, etc
		if ( button.conf.destroy ) {
			button.conf.destroy.call( dt.button(node), dt, $(node), button.conf );
		}

		this._removeKey( button.conf );

		$(button.node).remove();

		var idx = $.inArray( button, host );
		host.splice( idx, 1 );

		return this;
	},

	/**
	 * Get the text for a button
	 * @param  {int|string} node Button index
	 * @return {string} Button text
	 *//**
	 * Set the text for a button
	 * @param  {int|string|function} node Button index
	 * @param  {string} label Text
	 * @return {Buttons} Self for chaining
	 */
	text: function ( node, label )
	{
		var button = this._nodeToButton( node );
		var buttonLiner = this.c.dom.collection.buttonLiner;
		var linerTag = button.inCollection && buttonLiner && buttonLiner.tag ?
			buttonLiner.tag :
			this.c.dom.buttonLiner.tag;
		var dt = this.s.dt;
		var jqNode = $(button.node);
		var text = function ( opt ) {
			return typeof opt === 'function' ?
				opt( dt, jqNode, button.conf ) :
				opt;
		};

		if ( label === undefined ) {
			return text( button.conf.text );
		}

		button.conf.text = label;

		if ( linerTag ) {
			jqNode.children( linerTag ).html( text(label) );
		}
		else {
			jqNode.html( text(label) );
		}

		return this;
	},


	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Constructor
	 */

	/**
	 * Buttons constructor
	 * @private
	 */
	_constructor: function ()
	{
		var that = this;
		var dt = this.s.dt;
		var dtSettings = dt.settings()[0];
		var buttons =  this.c.buttons;

		if ( ! dtSettings._buttons ) {
			dtSettings._buttons = [];
		}

		dtSettings._buttons.push( {
			inst: this,
			name: this.c.name
		} );

		for ( var i=0, ien=buttons.length ; i<ien ; i++ ) {
			this.add( buttons[i] );
		}

		dt.on( 'destroy', function () {
			that.destroy();
		} );

		// Global key event binding to listen for button keys
		$('body').on( 'keyup.'+this.s.namespace, function ( e ) {
			if ( ! document.activeElement || document.activeElement === document.body ) {
				// SUse a string of characters for fast lookup of if we need to
				// handle this
				var character = String.fromCharCode(e.keyCode).toLowerCase();

				if ( that.s.listenKeys.toLowerCase().indexOf( character ) !== -1 ) {
					that._keypress( character, e );
				}
			}
		} );
	},


	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Private methods
	 */

	/**
	 * Add a new button to the key press listener
	 * @param {object} conf Resolved button configuration object
	 * @private
	 */
	_addKey: function ( conf )
	{
		if ( conf.key ) {
			this.s.listenKeys += $.isPlainObject( conf.key ) ?
				conf.key.key :
				conf.key;
		}
	},

	/**
	 * Insert the buttons into the container. Call without parameters!
	 * @param  {node} [container] Recursive only - Insert point
	 * @param  {array} [buttons] Recursive only - Buttons array
	 * @private
	 */
	_draw: function ( container, buttons )
	{
		if ( ! container ) {
			container = this.dom.container;
			buttons = this.s.buttons;
		}

		container.children().detach();

		for ( var i=0, ien=buttons.length ; i<ien ; i++ ) {
			container.append( buttons[i].inserter );
			container.append( ' ' );

			if ( buttons[i].buttons && buttons[i].buttons.length ) {
				this._draw( buttons[i].collection, buttons[i].buttons );
			}
		}
	},

	/**
	 * Create buttons from an array of buttons
	 * @param  {array} attachTo Buttons array to attach to
	 * @param  {object} button Button definition
	 * @param  {boolean} inCollection true if the button is in a collection
	 * @private
	 */
	_expandButton: function ( attachTo, button, inCollection, attachPoint )
	{
		var dt = this.s.dt;
		var buttonCounter = 0;
		var buttons = ! $.isArray( button ) ?
			[ button ] :
			button;

		for ( var i=0, ien=buttons.length ; i<ien ; i++ ) {
			var conf = this._resolveExtends( buttons[i] );

			if ( ! conf ) {
				continue;
			}

			// If the configuration is an array, then expand the buttons at this
			// point
			if ( $.isArray( conf ) ) {
				this._expandButton( attachTo, conf, inCollection, attachPoint );
				continue;
			}

			var built = this._buildButton( conf, inCollection );
			if ( ! built ) {
				continue;
			}

			if ( attachPoint !== undefined ) {
				attachTo.splice( attachPoint, 0, built );
				attachPoint++;
			}
			else {
				attachTo.push( built );
			}

			if ( built.conf.buttons ) {
				var collectionDom = this.c.dom.collection;
				built.collection = $('<'+collectionDom.tag+'/>')
					.addClass( collectionDom.className )
					.attr( 'role', 'menu') ;
				built.conf._collection = built.collection;

				this._expandButton( built.buttons, built.conf.buttons, true, attachPoint );
			}

			// init call is made here, rather than buildButton as it needs to
			// be selectable, and for that it needs to be in the buttons array
			if ( conf.init ) {
				conf.init.call( dt.button( built.node ), dt, $(built.node), conf );
			}

			buttonCounter++;
		}
	},

	/**
	 * Create an individual button
	 * @param  {object} config            Resolved button configuration
	 * @param  {boolean} inCollection `true` if a collection button
	 * @return {jQuery} Created button node (jQuery)
	 * @private
	 */
	_buildButton: function ( config, inCollection )
	{
		var buttonDom = this.c.dom.button;
		var linerDom = this.c.dom.buttonLiner;
		var collectionDom = this.c.dom.collection;
		var dt = this.s.dt;
		var text = function ( opt ) {
			return typeof opt === 'function' ?
				opt( dt, button, config ) :
				opt;
		};

		if ( inCollection && collectionDom.button ) {
			buttonDom = collectionDom.button;
		}

		if ( inCollection && collectionDom.buttonLiner ) {
			linerDom = collectionDom.buttonLiner;
		}

		// Make sure that the button is available based on whatever requirements
		// it has. For example, Flash buttons require Flash
		if ( config.available && ! config.available( dt, config ) ) {
			return false;
		}

		var action = function ( e, dt, button, config ) {
			config.action.call( dt.button( button ), e, dt, button, config );

			$(dt.table().node()).triggerHandler( 'buttons-action.dt', [
				dt.button( button ), dt, button, config 
			] );
		};

		var button = $('<'+buttonDom.tag+'/>')
			.addClass( buttonDom.className )
			.attr( 'tabindex', this.s.dt.settings()[0].iTabIndex )
			.attr( 'aria-controls', this.s.dt.table().node().id )
			.on( 'click.dtb', function (e) {
				e.preventDefault();

				if ( ! button.hasClass( buttonDom.disabled ) && config.action ) {
					action( e, dt, button, config );
				}

				button.blur();
			} )
			.on( 'keyup.dtb', function (e) {
				if ( e.keyCode === 13 ) {
					if ( ! button.hasClass( buttonDom.disabled ) && config.action ) {
						action( e, dt, button, config );
					}
				}
			} );

		// Make `a` tags act like a link
		if ( buttonDom.tag.toLowerCase() === 'a' ) {
			button.attr( 'href', '#' );
		}

		if ( linerDom.tag ) {
			var liner = $('<'+linerDom.tag+'/>')
				.html( text( config.text ) )
				.addClass( linerDom.className );

			if ( linerDom.tag.toLowerCase() === 'a' ) {
				liner.attr( 'href', '#' );
			}

			button.append( liner );
		}
		else {
			button.html( text( config.text ) );
		}

		if ( config.enabled === false ) {
			button.addClass( buttonDom.disabled );
		}

		if ( config.className ) {
			button.addClass( config.className );
		}

		if ( config.titleAttr ) {
			button.attr( 'title', text( config.titleAttr ) );
		}

		if ( config.attr ) {
			button.attr( config.attr );
		}

		if ( ! config.namespace ) {
			config.namespace = '.dt-button-'+(_buttonCounter++);
		}

		var buttonContainer = this.c.dom.buttonContainer;
		var inserter;
		if ( buttonContainer && buttonContainer.tag ) {
			inserter = $('<'+buttonContainer.tag+'/>')
				.addClass( buttonContainer.className )
				.append( button );
		}
		else {
			inserter = button;
		}

		this._addKey( config );

		return {
			conf:         config,
			node:         button.get(0),
			inserter:     inserter,
			buttons:      [],
			inCollection: inCollection,
			collection:   null
		};
	},

	/**
	 * Get the button object from a node (recursive)
	 * @param  {node} node Button node
	 * @param  {array} [buttons] Button array, uses base if not defined
	 * @return {object} Button object
	 * @private
	 */
	_nodeToButton: function ( node, buttons )
	{
		if ( ! buttons ) {
			buttons = this.s.buttons;
		}

		for ( var i=0, ien=buttons.length ; i<ien ; i++ ) {
			if ( buttons[i].node === node ) {
				return buttons[i];
			}

			if ( buttons[i].buttons.length ) {
				var ret = this._nodeToButton( node, buttons[i].buttons );

				if ( ret ) {
					return ret;
				}
			}
		}
	},

	/**
	 * Get container array for a button from a button node (recursive)
	 * @param  {node} node Button node
	 * @param  {array} [buttons] Button array, uses base if not defined
	 * @return {array} Button's host array
	 * @private
	 */
	_nodeToHost: function ( node, buttons )
	{
		if ( ! buttons ) {
			buttons = this.s.buttons;
		}

		for ( var i=0, ien=buttons.length ; i<ien ; i++ ) {
			if ( buttons[i].node === node ) {
				return buttons;
			}

			if ( buttons[i].buttons.length ) {
				var ret = this._nodeToHost( node, buttons[i].buttons );

				if ( ret ) {
					return ret;
				}
			}
		}
	},

	/**
	 * Handle a key press - determine if any button's key configured matches
	 * what was typed and trigger the action if so.
	 * @param  {string} character The character pressed
	 * @param  {object} e Key event that triggered this call
	 * @private
	 */
	_keypress: function ( character, e )
	{
		// Check if this button press already activated on another instance of Buttons
		if ( e._buttonsHandled ) {
			return;
		}

		var run = function ( conf, node ) {
			if ( ! conf.key ) {
				return;
			}

			if ( conf.key === character ) {
				e._buttonsHandled = true;
				$(node).click();
			}
			else if ( $.isPlainObject( conf.key ) ) {
				if ( conf.key.key !== character ) {
					return;
				}

				if ( conf.key.shiftKey && ! e.shiftKey ) {
					return;
				}

				if ( conf.key.altKey && ! e.altKey ) {
					return;
				}

				if ( conf.key.ctrlKey && ! e.ctrlKey ) {
					return;
				}

				if ( conf.key.metaKey && ! e.metaKey ) {
					return;
				}

				// Made it this far - it is good
				e._buttonsHandled = true;
				$(node).click();
			}
		};

		var recurse = function ( a ) {
			for ( var i=0, ien=a.length ; i<ien ; i++ ) {
				run( a[i].conf, a[i].node );

				if ( a[i].buttons.length ) {
					recurse( a[i].buttons );
				}
			}
		};

		recurse( this.s.buttons );
	},

	/**
	 * Remove a key from the key listener for this instance (to be used when a
	 * button is removed)
	 * @param  {object} conf Button configuration
	 * @private
	 */
	_removeKey: function ( conf )
	{
		if ( conf.key ) {
			var character = $.isPlainObject( conf.key ) ?
				conf.key.key :
				conf.key;

			// Remove only one character, as multiple buttons could have the
			// same listening key
			var a = this.s.listenKeys.split('');
			var idx = $.inArray( character, a );
			a.splice( idx, 1 );
			this.s.listenKeys = a.join('');
		}
	},

	/**
	 * Resolve a button configuration
	 * @param  {string|function|object} conf Button config to resolve
	 * @return {object} Button configuration
	 * @private
	 */
	_resolveExtends: function ( conf )
	{
		var dt = this.s.dt;
		var i, ien;
		var toConfObject = function ( base ) {
			var loop = 0;

			// Loop until we have resolved to a button configuration, or an
			// array of button configurations (which will be iterated
			// separately)
			while ( ! $.isPlainObject(base) && ! $.isArray(base) ) {
				if ( base === undefined ) {
					return;
				}

				if ( typeof base === 'function' ) {
					base = base( dt, conf );

					if ( ! base ) {
						return false;
					}
				}
				else if ( typeof base === 'string' ) {
					if ( ! _dtButtons[ base ] ) {
						throw 'Unknown button type: '+base;
					}

					base = _dtButtons[ base ];
				}

				loop++;
				if ( loop > 30 ) {
					// Protect against misconfiguration killing the browser
					throw 'Buttons: Too many iterations';
				}
			}

			return $.isArray( base ) ?
				base :
				$.extend( {}, base );
		};

		conf = toConfObject( conf );

		while ( conf && conf.extend ) {
			// Use `toConfObject` in case the button definition being extended
			// is itself a string or a function
			if ( ! _dtButtons[ conf.extend ] ) {
				throw 'Cannot extend unknown button type: '+conf.extend;
			}

			var objArray = toConfObject( _dtButtons[ conf.extend ] );
			if ( $.isArray( objArray ) ) {
				return objArray;
			}
			else if ( ! objArray ) {
				// This is a little brutal as it might be possible to have a
				// valid button without the extend, but if there is no extend
				// then the host button would be acting in an undefined state
				return false;
			}

			// Stash the current class name
			var originalClassName = objArray.className;

			conf = $.extend( {}, objArray, conf );

			// The extend will have overwritten the original class name if the
			// `conf` object also assigned a class, but we want to concatenate
			// them so they are list that is combined from all extended buttons
			if ( originalClassName && conf.className !== originalClassName ) {
				conf.className = originalClassName+' '+conf.className;
			}

			// Buttons to be added to a collection  -gives the ability to define
			// if buttons should be added to the start or end of a collection
			var postfixButtons = conf.postfixButtons;
			if ( postfixButtons ) {
				if ( ! conf.buttons ) {
					conf.buttons = [];
				}

				for ( i=0, ien=postfixButtons.length ; i<ien ; i++ ) {
					conf.buttons.push( postfixButtons[i] );
				}

				conf.postfixButtons = null;
			}

			var prefixButtons = conf.prefixButtons;
			if ( prefixButtons ) {
				if ( ! conf.buttons ) {
					conf.buttons = [];
				}

				for ( i=0, ien=prefixButtons.length ; i<ien ; i++ ) {
					conf.buttons.splice( i, 0, prefixButtons[i] );
				}

				conf.prefixButtons = null;
			}

			// Although we want the `conf` object to overwrite almost all of
			// the properties of the object being extended, the `extend`
			// property should come from the object being extended
			conf.extend = objArray.extend;
		}

		return conf;
	}
} );



/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
 * Statics
 */

/**
 * Show / hide a background layer behind a collection
 * @param  {boolean} Flag to indicate if the background should be shown or
 *   hidden 
 * @param  {string} Class to assign to the background
 * @static
 */
Buttons.background = function ( show, className, fade ) {
	if ( fade === undefined ) {
		fade = 400;
	}

	if ( show ) {
		$('<div/>')
			.addClass( className )
			.css( 'display', 'none' )
			.appendTo( 'body' )
			.fadeIn( fade );
	}
	else {
		$('body > div.'+className)
			.fadeOut( fade, function () {
				$(this)
					.removeClass( className )
					.remove();
			} );
	}
};

/**
 * Instance selector - select Buttons instances based on an instance selector
 * value from the buttons assigned to a DataTable. This is only useful if
 * multiple instances are attached to a DataTable.
 * @param  {string|int|array} Instance selector - see `instance-selector`
 *   documentation on the DataTables site
 * @param  {array} Button instance array that was attached to the DataTables
 *   settings object
 * @return {array} Buttons instances
 * @static
 */
Buttons.instanceSelector = function ( group, buttons )
{
	if ( ! group ) {
		return $.map( buttons, function ( v ) {
			return v.inst;
		} );
	}

	var ret = [];
	var names = $.map( buttons, function ( v ) {
		return v.name;
	} );

	// Flatten the group selector into an array of single options
	var process = function ( input ) {
		if ( $.isArray( input ) ) {
			for ( var i=0, ien=input.length ; i<ien ; i++ ) {
				process( input[i] );
			}
			return;
		}

		if ( typeof input === 'string' ) {
			if ( input.indexOf( ',' ) !== -1 ) {
				// String selector, list of names
				process( input.split(',') );
			}
			else {
				// String selector individual name
				var idx = $.inArray( $.trim(input), names );

				if ( idx !== -1 ) {
					ret.push( buttons[ idx ].inst );
				}
			}
		}
		else if ( typeof input === 'number' ) {
			// Index selector
			ret.push( buttons[ input ].inst );
		}
	};
	
	process( group );

	return ret;
};

/**
 * Button selector - select one or more buttons from a selector input so some
 * operation can be performed on them.
 * @param  {array} Button instances array that the selector should operate on
 * @param  {string|int|node|jQuery|array} Button selector - see
 *   `button-selector` documentation on the DataTables site
 * @return {array} Array of objects containing `inst` and `idx` properties of
 *   the selected buttons so you know which instance each button belongs to.
 * @static
 */
Buttons.buttonSelector = function ( insts, selector )
{
	var ret = [];
	var nodeBuilder = function ( a, buttons, baseIdx ) {
		var button;
		var idx;

		for ( var i=0, ien=buttons.length ; i<ien ; i++ ) {
			button = buttons[i];

			if ( button ) {
				idx = baseIdx !== undefined ?
					baseIdx+i :
					i+'';

				a.push( {
					node: button.node,
					name: button.conf.name,
					idx:  idx
				} );

				if ( button.buttons ) {
					nodeBuilder( a, button.buttons, idx+'-' );
				}
			}
		}
	};

	var run = function ( selector, inst ) {
		var i, ien;
		var buttons = [];
		nodeBuilder( buttons, inst.s.buttons );

		var nodes = $.map( buttons, function (v) {
			return v.node;
		} );

		if ( $.isArray( selector ) || selector instanceof $ ) {
			for ( i=0, ien=selector.length ; i<ien ; i++ ) {
				run( selector[i], inst );
			}
			return;
		}

		if ( selector === null || selector === undefined || selector === '*' ) {
			// Select all
			for ( i=0, ien=buttons.length ; i<ien ; i++ ) {
				ret.push( {
					inst: inst,
					node: buttons[i].node
				} );
			}
		}
		else if ( typeof selector === 'number' ) {
			// Main button index selector
			ret.push( {
				inst: inst,
				node: inst.s.buttons[ selector ].node
			} );
		}
		else if ( typeof selector === 'string' ) {
			if ( selector.indexOf( ',' ) !== -1 ) {
				// Split
				var a = selector.split(',');

				for ( i=0, ien=a.length ; i<ien ; i++ ) {
					run( $.trim(a[i]), inst );
				}
			}
			else if ( selector.match( /^\d+(\-\d+)*$/ ) ) {
				// Sub-button index selector
				var indexes = $.map( buttons, function (v) {
					return v.idx;
				} );

				ret.push( {
					inst: inst,
					node: buttons[ $.inArray( selector, indexes ) ].node
				} );
			}
			else if ( selector.indexOf( ':name' ) !== -1 ) {
				// Button name selector
				var name = selector.replace( ':name', '' );

				for ( i=0, ien=buttons.length ; i<ien ; i++ ) {
					if ( buttons[i].name === name ) {
						ret.push( {
							inst: inst,
							node: buttons[i].node
						} );
					}
				}
			}
			else {
				// jQuery selector on the nodes
				$( nodes ).filter( selector ).each( function () {
					ret.push( {
						inst: inst,
						node: this
					} );
				} );
			}
		}
		else if ( typeof selector === 'object' && selector.nodeName ) {
			// Node selector
			var idx = $.inArray( selector, nodes );

			if ( idx !== -1 ) {
				ret.push( {
					inst: inst,
					node: nodes[ idx ]
				} );
			}
		}
	};


	for ( var i=0, ien=insts.length ; i<ien ; i++ ) {
		var inst = insts[i];

		run( selector, inst );
	}

	return ret;
};


/**
 * Buttons defaults. For full documentation, please refer to the docs/option
 * directory or the DataTables site.
 * @type {Object}
 * @static
 */
Buttons.defaults = {
	buttons: [ 'copy', 'excel', 'csv', 'pdf', 'print' ],
	name: 'main',
	tabIndex: 0,
	dom: {
		container: {
			tag: 'div',
			className: 'dt-buttons'
		},
		collection: {
			tag: 'div',
			className: 'dt-button-collection'
		},
		button: {
			tag: 'button',
			className: 'dt-button',
			active: 'active',
			disabled: 'disabled'
		},
		buttonLiner: {
			tag: 'span',
			className: ''
		}
	}
};

/**
 * Version information
 * @type {string}
 * @static
 */
Buttons.version = '1.5.1';


$.extend( _dtButtons, {
	collection: {
		text: function ( dt ) {
			return dt.i18n( 'buttons.collection', 'Collection' );
		},
		className: 'buttons-collection',
		action: function ( e, dt, button, config ) {
			var host = button;
			var collectionParent = $(button).parents('div.dt-button-collection');
			var hostPosition = host.position();
			var tableContainer = $( dt.table().container() );
			var multiLevel = false;
			var insertPoint = host;

			// Remove any old collection
			if ( collectionParent.length ) {
				multiLevel = $('.dt-button-collection').position();
				insertPoint = collectionParent;
				$('body').trigger( 'click.dtb-collection' );
			}

			config._collection
				.addClass( config.collectionLayout )
				.css( 'display', 'none' )
				.insertAfter( insertPoint )
				.fadeIn( config.fade );
			

			var position = config._collection.css( 'position' );

			if ( multiLevel && position === 'absolute' ) {
				config._collection.css( {
					top: multiLevel.top,
					left: multiLevel.left
				} );
			}
			else if ( position === 'absolute' ) {
				config._collection.css( {
					top: hostPosition.top + host.outerHeight(),
					left: hostPosition.left
				} );

				// calculate overflow when positioned beneath
				var tableBottom = tableContainer.offset().top + tableContainer.height();
				var listBottom = hostPosition.top + host.outerHeight() + config._collection.outerHeight();
				var bottomOverflow = listBottom - tableBottom;
				
				// calculate overflow when positioned above
				var listTop = hostPosition.top - config._collection.outerHeight();
				var tableTop = tableContainer.offset().top;
				var topOverflow = tableTop - listTop;
				
				// if bottom overflow is larger, move to the top because it fits better
				if (bottomOverflow > topOverflow) {
					config._collection.css( 'top', hostPosition.top - config._collection.outerHeight() - 5);
				}

				var listRight = hostPosition.left + config._collection.outerWidth();
				var tableRight = tableContainer.offset().left + tableContainer.width();
				if ( listRight > tableRight ) {
					config._collection.css( 'left', hostPosition.left - ( listRight - tableRight ) );
				}
			}
			else {
				// Fix position - centre on screen
				var top = config._collection.height() / 2;
				if ( top > $(window).height() / 2 ) {
					top = $(window).height() / 2;
				}

				config._collection.css( 'marginTop', top*-1 );
			}

			if ( config.background ) {
				Buttons.background( true, config.backgroundClassName, config.fade );
			}

			// Need to break the 'thread' for the collection button being
			// activated by a click - it would also trigger this event
			setTimeout( function () {
				// This is bonkers, but if we don't have a click listener on the
				// background element, iOS Safari will ignore the body click
				// listener below. An empty function here is all that is
				// required to make it work...
				$('div.dt-button-background').on( 'click.dtb-collection', function () {} );

				$('body').on( 'click.dtb-collection', function (e) {
					// andSelf is deprecated in jQ1.8, but we want 1.7 compat
					var back = $.fn.addBack ? 'addBack' : 'andSelf';

					if ( ! $(e.target).parents()[back]().filter( config._collection ).length ) {
						config._collection
							.fadeOut( config.fade, function () {
								config._collection.detach();
							} );

						$('div.dt-button-background').off( 'click.dtb-collection' );
						Buttons.background( false, config.backgroundClassName, config.fade );

						$('body').off( 'click.dtb-collection' );
						dt.off( 'buttons-action.b-internal' );
					}
				} );
			}, 10 );

			if ( config.autoClose ) {
				dt.on( 'buttons-action.b-internal', function () {
					$('div.dt-button-background').click();
				} );
			}
		},
		background: true,
		collectionLayout: '',
		backgroundClassName: 'dt-button-background',
		autoClose: false,
		fade: 400,
		attr: {
			'aria-haspopup': true
		}
	},
	copy: function ( dt, conf ) {
		if ( _dtButtons.copyHtml5 ) {
			return 'copyHtml5';
		}
		if ( _dtButtons.copyFlash && _dtButtons.copyFlash.available( dt, conf ) ) {
			return 'copyFlash';
		}
	},
	csv: function ( dt, conf ) {
		// Common option that will use the HTML5 or Flash export buttons
		if ( _dtButtons.csvHtml5 && _dtButtons.csvHtml5.available( dt, conf ) ) {
			return 'csvHtml5';
		}
		if ( _dtButtons.csvFlash && _dtButtons.csvFlash.available( dt, conf ) ) {
			return 'csvFlash';
		}
	},
	excel: function ( dt, conf ) {
		// Common option that will use the HTML5 or Flash export buttons
		if ( _dtButtons.excelHtml5 && _dtButtons.excelHtml5.available( dt, conf ) ) {
			return 'excelHtml5';
		}
		if ( _dtButtons.excelFlash && _dtButtons.excelFlash.available( dt, conf ) ) {
			return 'excelFlash';
		}
	},
	pdf: function ( dt, conf ) {
		// Common option that will use the HTML5 or Flash export buttons
		if ( _dtButtons.pdfHtml5 && _dtButtons.pdfHtml5.available( dt, conf ) ) {
			return 'pdfHtml5';
		}
		if ( _dtButtons.pdfFlash && _dtButtons.pdfFlash.available( dt, conf ) ) {
			return 'pdfFlash';
		}
	},
	pageLength: function ( dt ) {
		var lengthMenu = dt.settings()[0].aLengthMenu;
		var vals = $.isArray( lengthMenu[0] ) ? lengthMenu[0] : lengthMenu;
		var lang = $.isArray( lengthMenu[0] ) ? lengthMenu[1] : lengthMenu;
		var text = function ( dt ) {
			return dt.i18n( 'buttons.pageLength', {
				"-1": 'Show all rows',
				_:    'Show %d rows'
			}, dt.page.len() );
		};

		return {
			extend: 'collection',
			text: text,
			className: 'buttons-page-length',
			autoClose: true,
			buttons: $.map( vals, function ( val, i ) {
				return {
					text: lang[i],
					className: 'button-page-length',
					action: function ( e, dt ) {
						dt.page.len( val ).draw();
					},
					init: function ( dt, node, conf ) {
						var that = this;
						var fn = function () {
							that.active( dt.page.len() === val );
						};

						dt.on( 'length.dt'+conf.namespace, fn );
						fn();
					},
					destroy: function ( dt, node, conf ) {
						dt.off( 'length.dt'+conf.namespace );
					}
				};
			} ),
			init: function ( dt, node, conf ) {
				var that = this;
				dt.on( 'length.dt'+conf.namespace, function () {
					that.text( text( dt ) );
				} );
			},
			destroy: function ( dt, node, conf ) {
				dt.off( 'length.dt'+conf.namespace );
			}
		};
	}
} );


/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
 * DataTables API
 *
 * For complete documentation, please refer to the docs/api directory or the
 * DataTables site
 */

// Buttons group and individual button selector
DataTable.Api.register( 'buttons()', function ( group, selector ) {
	// Argument shifting
	if ( selector === undefined ) {
		selector = group;
		group = undefined;
	}

	this.selector.buttonGroup = group;

	var res = this.iterator( true, 'table', function ( ctx ) {
		if ( ctx._buttons ) {
			return Buttons.buttonSelector(
				Buttons.instanceSelector( group, ctx._buttons ),
				selector
			);
		}
	}, true );

	res._groupSelector = group;
	return res;
} );

// Individual button selector
DataTable.Api.register( 'button()', function ( group, selector ) {
	// just run buttons() and truncate
	var buttons = this.buttons( group, selector );

	if ( buttons.length > 1 ) {
		buttons.splice( 1, buttons.length );
	}

	return buttons;
} );

// Active buttons
DataTable.Api.registerPlural( 'buttons().active()', 'button().active()', function ( flag ) {
	if ( flag === undefined ) {
		return this.map( function ( set ) {
			return set.inst.active( set.node );
		} );
	}

	return this.each( function ( set ) {
		set.inst.active( set.node, flag );
	} );
} );

// Get / set button action
DataTable.Api.registerPlural( 'buttons().action()', 'button().action()', function ( action ) {
	if ( action === undefined ) {
		return this.map( function ( set ) {
			return set.inst.action( set.node );
		} );
	}

	return this.each( function ( set ) {
		set.inst.action( set.node, action );
	} );
} );

// Enable / disable buttons
DataTable.Api.register( ['buttons().enable()', 'button().enable()'], function ( flag ) {
	return this.each( function ( set ) {
		set.inst.enable( set.node, flag );
	} );
} );

// Disable buttons
DataTable.Api.register( ['buttons().disable()', 'button().disable()'], function () {
	return this.each( function ( set ) {
		set.inst.disable( set.node );
	} );
} );

// Get button nodes
DataTable.Api.registerPlural( 'buttons().nodes()', 'button().node()', function () {
	var jq = $();

	// jQuery will automatically reduce duplicates to a single entry
	$( this.each( function ( set ) {
		jq = jq.add( set.inst.node( set.node ) );
	} ) );

	return jq;
} );

// Get / set button processing state
DataTable.Api.registerPlural( 'buttons().processing()', 'button().processing()', function ( flag ) {
	if ( flag === undefined ) {
		return this.map( function ( set ) {
			return set.inst.processing( set.node );
		} );
	}

	return this.each( function ( set ) {
		set.inst.processing( set.node, flag );
	} );
} );

// Get / set button text (i.e. the button labels)
DataTable.Api.registerPlural( 'buttons().text()', 'button().text()', function ( label ) {
	if ( label === undefined ) {
		return this.map( function ( set ) {
			return set.inst.text( set.node );
		} );
	}

	return this.each( function ( set ) {
		set.inst.text( set.node, label );
	} );
} );

// Trigger a button's action
DataTable.Api.registerPlural( 'buttons().trigger()', 'button().trigger()', function () {
	return this.each( function ( set ) {
		set.inst.node( set.node ).trigger( 'click' );
	} );
} );

// Get the container elements
DataTable.Api.registerPlural( 'buttons().containers()', 'buttons().container()', function () {
	var jq = $();
	var groupSelector = this._groupSelector;

	// We need to use the group selector directly, since if there are no buttons
	// the result set will be empty
	this.iterator( true, 'table', function ( ctx ) {
		if ( ctx._buttons ) {
			var insts = Buttons.instanceSelector( groupSelector, ctx._buttons );

			for ( var i=0, ien=insts.length ; i<ien ; i++ ) {
				jq = jq.add( insts[i].container() );
			}
		}
	} );

	return jq;
} );

// Add a new button
DataTable.Api.register( 'button().add()', function ( idx, conf ) {
	var ctx = this.context;

	// Don't use `this` as it could be empty - select the instances directly
	if ( ctx.length ) {
		var inst = Buttons.instanceSelector( this._groupSelector, ctx[0]._buttons );

		if ( inst.length ) {
			inst[0].add( conf, idx );
		}
	}

	return this.button( this._groupSelector, idx );
} );

// Destroy the button sets selected
DataTable.Api.register( 'buttons().destroy()', function () {
	this.pluck( 'inst' ).unique().each( function ( inst ) {
		inst.destroy();
	} );

	return this;
} );

// Remove a button
DataTable.Api.registerPlural( 'buttons().remove()', 'buttons().remove()', function () {
	this.each( function ( set ) {
		set.inst.remove( set.node );
	} );

	return this;
} );

// Information box that can be used by buttons
var _infoTimer;
DataTable.Api.register( 'buttons.info()', function ( title, message, time ) {
	var that = this;

	if ( title === false ) {
		$('#datatables_buttons_info').fadeOut( function () {
			$(this).remove();
		} );
		clearTimeout( _infoTimer );
		_infoTimer = null;

		return this;
	}

	if ( _infoTimer ) {
		clearTimeout( _infoTimer );
	}

	if ( $('#datatables_buttons_info').length ) {
		$('#datatables_buttons_info').remove();
	}

	title = title ? '<h2>'+title+'</h2>' : '';

	$('<div id="datatables_buttons_info" class="dt-button-info"/>')
		.html( title )
		.append( $('<div/>')[ typeof message === 'string' ? 'html' : 'append' ]( message ) )
		.css( 'display', 'none' )
		.appendTo( 'body' )
		.fadeIn();

	if ( time !== undefined && time !== 0 ) {
		_infoTimer = setTimeout( function () {
			that.buttons.info( false );
		}, time );
	}

	return this;
} );

// Get data from the table for export - this is common to a number of plug-in
// buttons so it is included in the Buttons core library
DataTable.Api.register( 'buttons.exportData()', function ( options ) {
	if ( this.context.length ) {
		return _exportData( new DataTable.Api( this.context[0] ), options );
	}
} );

// Get information about the export that is common to many of the export data
// types (DRY)
DataTable.Api.register( 'buttons.exportInfo()', function ( conf ) {
	if ( ! conf ) {
		conf = {};
	}

	return {
		filename: _filename( conf ),
		title: _title( conf ),
		messageTop: _message(this, conf.message || conf.messageTop, 'top'),
		messageBottom: _message(this, conf.messageBottom, 'bottom')
	};
} );



/**
 * Get the file name for an exported file.
 *
 * @param {object}	config Button configuration
 * @param {boolean} incExtension Include the file name extension
 */
var _filename = function ( config )
{
	// Backwards compatibility
	var filename = config.filename === '*' && config.title !== '*' && config.title !== undefined && config.title !== null && config.title !== '' ?
		config.title :
		config.filename;

	if ( typeof filename === 'function' ) {
		filename = filename();
	}

	if ( filename === undefined || filename === null ) {
		return null;
	}

	if ( filename.indexOf( '*' ) !== -1 ) {
		filename = $.trim( filename.replace( '*', $('head > title').text() ) );
	}

	// Strip characters which the OS will object to
	filename = filename.replace(/[^a-zA-Z0-9_\u00A1-\uFFFF\.,\-_ !\(\)]/g, "");

	var extension = _stringOrFunction( config.extension );
	if ( ! extension ) {
		extension = '';
	}

	return filename + extension;
};

/**
 * Simply utility method to allow parameters to be given as a function
 *
 * @param {undefined|string|function} option Option
 * @return {null|string} Resolved value
 */
var _stringOrFunction = function ( option )
{
	if ( option === null || option === undefined ) {
		return null;
	}
	else if ( typeof option === 'function' ) {
		return option();
	}
	return option;
};

/**
 * Get the title for an exported file.
 *
 * @param {object} config	Button configuration
 */
var _title = function ( config )
{
	var title = _stringOrFunction( config.title );

	return title === null ?
		null : title.indexOf( '*' ) !== -1 ?
			title.replace( '*', $('head > title').text() || 'Exported data' ) :
			title;
};

var _message = function ( dt, option, position )
{
	var message = _stringOrFunction( option );
	if ( message === null ) {
		return null;
	}

	var caption = $('caption', dt.table().container()).eq(0);
	if ( message === '*' ) {
		var side = caption.css( 'caption-side' );
		if ( side !== position ) {
			return null;
		}

		return caption.length ?
			caption.text() :
			'';
	}

	return message;
};







var _exportTextarea = $('<textarea/>')[0];
var _exportData = function ( dt, inOpts )
{
	var config = $.extend( true, {}, {
		rows:           null,
		columns:        '',
		modifier:       {
			search: 'applied',
			order:  'applied'
		},
		orthogonal:     'display',
		stripHtml:      true,
		stripNewlines:  true,
		decodeEntities: true,
		trim:           true,
		format:         {
			header: function ( d ) {
				return strip( d );
			},
			footer: function ( d ) {
				return strip( d );
			},
			body: function ( d ) {
				return strip( d );
			}
		}
	}, inOpts );

	var strip = function ( str ) {
		if ( typeof str !== 'string' ) {
			return str;
		}

		// Always remove script tags
		str = str.replace( /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '' );

		if ( config.stripHtml ) {
			str = str.replace( /<[^>]*>/g, '' );
		}

		if ( config.trim ) {
			str = str.replace( /^\s+|\s+$/g, '' );
		}

		if ( config.stripNewlines ) {
			str = str.replace( /\n/g, ' ' );
		}

		if ( config.decodeEntities ) {
			_exportTextarea.innerHTML = str;
			str = _exportTextarea.value;
		}

		return str;
	};


	var header = dt.columns( config.columns ).indexes().map( function (idx) {
		var el = dt.column( idx ).header();
		return config.format.header( el.innerHTML, idx, el );
	} ).toArray();

	var footer = dt.table().footer() ?
		dt.columns( config.columns ).indexes().map( function (idx) {
			var el = dt.column( idx ).footer();
			return config.format.footer( el ? el.innerHTML : '', idx, el );
		} ).toArray() :
		null;
	
	// If Select is available on this table, and any rows are selected, limit the export
	// to the selected rows. If no rows are selected, all rows will be exported. Specify
	// a `selected` modifier to control directly.
	var modifier = $.extend( {}, config.modifier );
	if ( dt.select && typeof dt.select.info === 'function' && modifier.selected === undefined ) {
		if ( dt.rows( config.rows, $.extend( { selected: true }, modifier ) ).any() ) {
			$.extend( modifier, { selected: true } )
		}
	}

	var rowIndexes = dt.rows( config.rows, modifier ).indexes().toArray();
	var selectedCells = dt.cells( rowIndexes, config.columns );
	var cells = selectedCells
		.render( config.orthogonal )
		.toArray();
	var cellNodes = selectedCells
		.nodes()
		.toArray();

	var columns = header.length;
	var rows = columns > 0 ? cells.length / columns : 0;
	var body = [ rows ];
	var cellCounter = 0;

	for ( var i=0, ien=rows ; i<ien ; i++ ) {
		var row = [ columns ];

		for ( var j=0 ; j<columns ; j++ ) {
			row[j] = config.format.body( cells[ cellCounter ], i, j, cellNodes[ cellCounter ] );
			cellCounter++;
		}

		body[i] = row;
	}

	return {
		header: header,
		footer: footer,
		body:   body
	};
};


/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
 * DataTables interface
 */

// Attach to DataTables objects for global access
$.fn.dataTable.Buttons = Buttons;
$.fn.DataTable.Buttons = Buttons;



// DataTables creation - check if the buttons have been defined for this table,
// they will have been if the `B` option was used in `dom`, otherwise we should
// create the buttons instance here so they can be inserted into the document
// using the API. Listen for `init` for compatibility with pre 1.10.10, but to
// be removed in future.
$(document).on( 'init.dt plugin-init.dt', function (e, settings) {
	if ( e.namespace !== 'dt' ) {
		return;
	}

	var opts = settings.oInit.buttons || DataTable.defaults.buttons;

	if ( opts && ! settings._buttons ) {
		new Buttons( settings, opts ).container();
	}
} );

// DataTables `dom` feature option
DataTable.ext.feature.push( {
	fnInit: function( settings ) {
		var api = new DataTable.Api( settings );
		var opts = api.init().buttons || DataTable.defaults.buttons;

		return new Buttons( api, opts ).container();
	},
	cFeature: "B"
} );


return Buttons;
}));


/*! Responsive 2.2.1
 * 2014-2017 SpryMedia Ltd - datatables.net/license
 */

/**
 * @summary     Responsive
 * @description Responsive tables plug-in for DataTables
 * @version     2.2.1
 * @file        dataTables.responsive.js
 * @author      SpryMedia Ltd (www.sprymedia.co.uk)
 * @contact     www.sprymedia.co.uk/contact
 * @copyright   Copyright 2014-2017 SpryMedia Ltd.
 *
 * This source file is free software, available under the following license:
 *   MIT license - http://datatables.net/license/mit
 *
 * This source file is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE. See the license files for details.
 *
 * For details please refer to: http://www.datatables.net
 */
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


/**
 * Responsive is a plug-in for the DataTables library that makes use of
 * DataTables' ability to change the visibility of columns, changing the
 * visibility of columns so the displayed columns fit into the table container.
 * The end result is that complex tables will be dynamically adjusted to fit
 * into the viewport, be it on a desktop, tablet or mobile browser.
 *
 * Responsive for DataTables has two modes of operation, which can used
 * individually or combined:
 *
 * * Class name based control - columns assigned class names that match the
 *   breakpoint logic can be shown / hidden as required for each breakpoint.
 * * Automatic control - columns are automatically hidden when there is no
 *   room left to display them. Columns removed from the right.
 *
 * In additional to column visibility control, Responsive also has built into
 * options to use DataTables' child row display to show / hide the information
 * from the table that has been hidden. There are also two modes of operation
 * for this child row display:
 *
 * * Inline - when the control element that the user can use to show / hide
 *   child rows is displayed inside the first column of the table.
 * * Column - where a whole column is dedicated to be the show / hide control.
 *
 * Initialisation of Responsive is performed by:
 *
 * * Adding the class `responsive` or `dt-responsive` to the table. In this case
 *   Responsive will automatically be initialised with the default configuration
 *   options when the DataTable is created.
 * * Using the `responsive` option in the DataTables configuration options. This
 *   can also be used to specify the configuration options, or simply set to
 *   `true` to use the defaults.
 *
 *  @class
 *  @param {object} settings DataTables settings object for the host table
 *  @param {object} [opts] Configuration options
 *  @requires jQuery 1.7+
 *  @requires DataTables 1.10.3+
 *
 *  @example
 *      $('#example').DataTable( {
 *        responsive: true
 *      } );
 *    } );
 */
var Responsive = function ( settings, opts ) {
	// Sanity check that we are using DataTables 1.10 or newer
	if ( ! DataTable.versionCheck || ! DataTable.versionCheck( '1.10.10' ) ) {
		throw 'DataTables Responsive requires DataTables 1.10.10 or newer';
	}

	this.s = {
		dt: new DataTable.Api( settings ),
		columns: [],
		current: []
	};

	// Check if responsive has already been initialised on this table
	if ( this.s.dt.settings()[0].responsive ) {
		return;
	}

	// details is an object, but for simplicity the user can give it as a string
	// or a boolean
	if ( opts && typeof opts.details === 'string' ) {
		opts.details = { type: opts.details };
	}
	else if ( opts && opts.details === false ) {
		opts.details = { type: false };
	}
	else if ( opts && opts.details === true ) {
		opts.details = { type: 'inline' };
	}

	this.c = $.extend( true, {}, Responsive.defaults, DataTable.defaults.responsive, opts );
	settings.responsive = this;
	this._constructor();
};

$.extend( Responsive.prototype, {
	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Constructor
	 */

	/**
	 * Initialise the Responsive instance
	 *
	 * @private
	 */
	_constructor: function ()
	{
		var that = this;
		var dt = this.s.dt;
		var dtPrivateSettings = dt.settings()[0];
		var oldWindowWidth = $(window).width();

		dt.settings()[0]._responsive = this;

		// Use DataTables' throttle function to avoid processor thrashing on
		// resize
		$(window).on( 'resize.dtr orientationchange.dtr', DataTable.util.throttle( function () {
			// iOS has a bug whereby resize can fire when only scrolling
			// See: http://stackoverflow.com/questions/8898412
			var width = $(window).width();

			if ( width !== oldWindowWidth ) {
				that._resize();
				oldWindowWidth = width;
			}
		} ) );

		// DataTables doesn't currently trigger an event when a row is added, so
		// we need to hook into its private API to enforce the hidden rows when
		// new data is added
		dtPrivateSettings.oApi._fnCallbackReg( dtPrivateSettings, 'aoRowCreatedCallback', function (tr, data, idx) {
			if ( $.inArray( false, that.s.current ) !== -1 ) {
				$('>td, >th', tr).each( function ( i ) {
					var idx = dt.column.index( 'toData', i );

					if ( that.s.current[idx] === false ) {
						$(this).css('display', 'none');
					}
				} );
			}
		} );

		// Destroy event handler
		dt.on( 'destroy.dtr', function () {
			dt.off( '.dtr' );
			$( dt.table().body() ).off( '.dtr' );
			$(window).off( 'resize.dtr orientationchange.dtr' );

			// Restore the columns that we've hidden
			$.each( that.s.current, function ( i, val ) {
				if ( val === false ) {
					that._setColumnVis( i, true );
				}
			} );
		} );

		// Reorder the breakpoints array here in case they have been added out
		// of order
		this.c.breakpoints.sort( function (a, b) {
			return a.width < b.width ? 1 :
				a.width > b.width ? -1 : 0;
		} );

		this._classLogic();
		this._resizeAuto();

		// Details handler
		var details = this.c.details;

		if ( details.type !== false ) {
			that._detailsInit();

			// DataTables will trigger this event on every column it shows and
			// hides individually
			dt.on( 'column-visibility.dtr', function (e, ctx, col, vis, recalc) {
				if ( recalc ) {
					that._classLogic();
					that._resizeAuto();
					that._resize();
				}
			} );

			// Redraw the details box on each draw which will happen if the data
			// has changed. This is used until DataTables implements a native
			// `updated` event for rows
			dt.on( 'draw.dtr', function () {
				that._redrawChildren();
			} );

			$(dt.table().node()).addClass( 'dtr-'+details.type );
		}

		dt.on( 'column-reorder.dtr', function (e, settings, details) {
			that._classLogic();
			that._resizeAuto();
			that._resize();
		} );

		// Change in column sizes means we need to calc
		dt.on( 'column-sizing.dtr', function () {
			that._resizeAuto();
			that._resize();
		});

		// On Ajax reload we want to reopen any child rows which are displayed
		// by responsive
		dt.on( 'preXhr.dtr', function () {
			var rowIds = [];
			dt.rows().every( function () {
				if ( this.child.isShown() ) {
					rowIds.push( this.id(true) );
				}
			} );

			dt.one( 'draw.dtr', function () {
				that._resizeAuto();
				that._resize();

				dt.rows( rowIds ).every( function () {
					that._detailsDisplay( this, false );
				} );
			} );
		});

		dt.on( 'init.dtr', function (e, settings, details) {
			that._resizeAuto();
			that._resize();

			// If columns were hidden, then DataTables needs to adjust the
			// column sizing
			if ( $.inArray( false, that.s.current ) ) {
				dt.columns.adjust();
			}
		} );

		// First pass - draw the table for the current viewport size
		this._resize();
	},


	/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
	 * Private methods
	 */

	/**
	 * Calculate the visibility for the columns in a table for a given
	 * breakpoint. The result is pre-determined based on the class logic if
	 * class names are used to control all columns, but the width of the table
	 * is also used if there are columns which are to be automatically shown
	 * and hidden.
	 *
	 * @param  {string} breakpoint Breakpoint name to use for the calculation
	 * @return {array} Array of boolean values initiating the visibility of each
	 *   column.
	 *  @private
	 */
	_columnsVisiblity: function ( breakpoint )
	{
		var dt = this.s.dt;
		var columns = this.s.columns;
		var i, ien;

		// Create an array that defines the column ordering based first on the
		// column's priority, and secondly the column index. This allows the
		// columns to be removed from the right if the priority matches
		var order = columns
			.map( function ( col, idx ) {
				return {
					columnIdx: idx,
					priority: col.priority
				};
			} )
			.sort( function ( a, b ) {
				if ( a.priority !== b.priority ) {
					return a.priority - b.priority;
				}
				return a.columnIdx - b.columnIdx;
			} );

		// Class logic - determine which columns are in this breakpoint based
		// on the classes. If no class control (i.e. `auto`) then `-` is used
		// to indicate this to the rest of the function
		var display = $.map( columns, function ( col ) {
			return col.auto && col.minWidth === null ?
				false :
				col.auto === true ?
					'-' :
					$.inArray( breakpoint, col.includeIn ) !== -1;
		} );

		// Auto column control - first pass: how much width is taken by the
		// ones that must be included from the non-auto columns
		var requiredWidth = 0;
		for ( i=0, ien=display.length ; i<ien ; i++ ) {
			if ( display[i] === true ) {
				requiredWidth += columns[i].minWidth;
			}
		}

		// Second pass, use up any remaining width for other columns. For
		// scrolling tables we need to subtract the width of the scrollbar. It
		// may not be requires which makes this sub-optimal, but it would
		// require another full redraw to make complete use of those extra few
		// pixels
		var scrolling = dt.settings()[0].oScroll;
		var bar = scrolling.sY || scrolling.sX ? scrolling.iBarWidth : 0;
		var widthAvailable = dt.table().container().offsetWidth - bar;
		var usedWidth = widthAvailable - requiredWidth;

		// Control column needs to always be included. This makes it sub-
		// optimal in terms of using the available with, but to stop layout
		// thrashing or overflow. Also we need to account for the control column
		// width first so we know how much width is available for the other
		// columns, since the control column might not be the first one shown
		for ( i=0, ien=display.length ; i<ien ; i++ ) {
			if ( columns[i].control ) {
				usedWidth -= columns[i].minWidth;
			}
		}

		// Allow columns to be shown (counting by priority and then right to
		// left) until we run out of room
		var empty = false;
		for ( i=0, ien=order.length ; i<ien ; i++ ) {
			var colIdx = order[i].columnIdx;

			if ( display[colIdx] === '-' && ! columns[colIdx].control && columns[colIdx].minWidth ) {
				// Once we've found a column that won't fit we don't let any
				// others display either, or columns might disappear in the
				// middle of the table
				if ( empty || usedWidth - columns[colIdx].minWidth < 0 ) {
					empty = true;
					display[colIdx] = false;
				}
				else {
					display[colIdx] = true;
				}

				usedWidth -= columns[colIdx].minWidth;
			}
		}

		// Determine if the 'control' column should be shown (if there is one).
		// This is the case when there is a hidden column (that is not the
		// control column). The two loops look inefficient here, but they are
		// trivial and will fly through. We need to know the outcome from the
		// first , before the action in the second can be taken
		var showControl = false;

		for ( i=0, ien=columns.length ; i<ien ; i++ ) {
			if ( ! columns[i].control && ! columns[i].never && ! display[i] ) {
				showControl = true;
				break;
			}
		}

		for ( i=0, ien=columns.length ; i<ien ; i++ ) {
			if ( columns[i].control ) {
				display[i] = showControl;
			}
		}

		// Finally we need to make sure that there is at least one column that
		// is visible
		if ( $.inArray( true, display ) === -1 ) {
			display[0] = true;
		}

		return display;
	},


	/**
	 * Create the internal `columns` array with information about the columns
	 * for the table. This includes determining which breakpoints the column
	 * will appear in, based upon class names in the column, which makes up the
	 * vast majority of this method.
	 *
	 * @private
	 */
	_classLogic: function ()
	{
		var that = this;
		var calc = {};
		var breakpoints = this.c.breakpoints;
		var dt = this.s.dt;
		var columns = dt.columns().eq(0).map( function (i) {
			var column = this.column(i);
			var className = column.header().className;
			var priority = dt.settings()[0].aoColumns[i].responsivePriority;

			if ( priority === undefined ) {
				var dataPriority = $(column.header()).data('priority');

				priority = dataPriority !== undefined ?
					dataPriority * 1 :
					10000;
			}

			return {
				className: className,
				includeIn: [],
				auto:      false,
				control:   false,
				never:     className.match(/\bnever\b/) ? true : false,
				priority:  priority
			};
		} );

		// Simply add a breakpoint to `includeIn` array, ensuring that there are
		// no duplicates
		var add = function ( colIdx, name ) {
			var includeIn = columns[ colIdx ].includeIn;

			if ( $.inArray( name, includeIn ) === -1 ) {
				includeIn.push( name );
			}
		};

		var column = function ( colIdx, name, operator, matched ) {
			var size, i, ien;

			if ( ! operator ) {
				columns[ colIdx ].includeIn.push( name );
			}
			else if ( operator === 'max-' ) {
				// Add this breakpoint and all smaller
				size = that._find( name ).width;

				for ( i=0, ien=breakpoints.length ; i<ien ; i++ ) {
					if ( breakpoints[i].width <= size ) {
						add( colIdx, breakpoints[i].name );
					}
				}
			}
			else if ( operator === 'min-' ) {
				// Add this breakpoint and all larger
				size = that._find( name ).width;

				for ( i=0, ien=breakpoints.length ; i<ien ; i++ ) {
					if ( breakpoints[i].width >= size ) {
						add( colIdx, breakpoints[i].name );
					}
				}
			}
			else if ( operator === 'not-' ) {
				// Add all but this breakpoint
				for ( i=0, ien=breakpoints.length ; i<ien ; i++ ) {
					if ( breakpoints[i].name.indexOf( matched ) === -1 ) {
						add( colIdx, breakpoints[i].name );
					}
				}
			}
		};

		// Loop over each column and determine if it has a responsive control
		// class
		columns.each( function ( col, i ) {
			var classNames = col.className.split(' ');
			var hasClass = false;

			// Split the class name up so multiple rules can be applied if needed
			for ( var k=0, ken=classNames.length ; k<ken ; k++ ) {
				var className = $.trim( classNames[k] );

				if ( className === 'all' ) {
					// Include in all
					hasClass = true;
					col.includeIn = $.map( breakpoints, function (a) {
						return a.name;
					} );
					return;
				}
				else if ( className === 'none' || col.never ) {
					// Include in none (default) and no auto
					hasClass = true;
					return;
				}
				else if ( className === 'control' ) {
					// Special column that is only visible, when one of the other
					// columns is hidden. This is used for the details control
					hasClass = true;
					col.control = true;
					return;
				}

				$.each( breakpoints, function ( j, breakpoint ) {
					// Does this column have a class that matches this breakpoint?
					var brokenPoint = breakpoint.name.split('-');
					var re = new RegExp( '(min\\-|max\\-|not\\-)?('+brokenPoint[0]+')(\\-[_a-zA-Z0-9])?' );
					var match = className.match( re );

					if ( match ) {
						hasClass = true;

						if ( match[2] === brokenPoint[0] && match[3] === '-'+brokenPoint[1] ) {
							// Class name matches breakpoint name fully
							column( i, breakpoint.name, match[1], match[2]+match[3] );
						}
						else if ( match[2] === brokenPoint[0] && ! match[3] ) {
							// Class name matched primary breakpoint name with no qualifier
							column( i, breakpoint.name, match[1], match[2] );
						}
					}
				} );
			}

			// If there was no control class, then automatic sizing is used
			if ( ! hasClass ) {
				col.auto = true;
			}
		} );

		this.s.columns = columns;
	},


	/**
	 * Show the details for the child row
	 *
	 * @param  {DataTables.Api} row    API instance for the row
	 * @param  {boolean}        update Update flag
	 * @private
	 */
	_detailsDisplay: function ( row, update )
	{
		var that = this;
		var dt = this.s.dt;
		var details = this.c.details;

		if ( details && details.type !== false ) {
			var res = details.display( row, update, function () {
				return details.renderer(
					dt, row[0], that._detailsObj(row[0])
				);
			} );

			if ( res === true || res === false ) {
				$(dt.table().node()).triggerHandler( 'responsive-display.dt', [dt, row, res, update] );
			}
		}
	},


	/**
	 * Initialisation for the details handler
	 *
	 * @private
	 */
	_detailsInit: function ()
	{
		var that    = this;
		var dt      = this.s.dt;
		var details = this.c.details;

		// The inline type always uses the first child as the target
		if ( details.type === 'inline' ) {
			details.target = 'td:first-child, th:first-child';
		}

		// Keyboard accessibility
		dt.on( 'draw.dtr', function () {
			that._tabIndexes();
		} );
		that._tabIndexes(); // Initial draw has already happened

		$( dt.table().body() ).on( 'keyup.dtr', 'td, th', function (e) {
			if ( e.keyCode === 13 && $(this).data('dtr-keyboard') ) {
				$(this).click();
			}
		} );

		// type.target can be a string jQuery selector or a column index
		var target   = details.target;
		var selector = typeof target === 'string' ? target : 'td, th';

		// Click handler to show / hide the details rows when they are available
		$( dt.table().body() )
			.on( 'click.dtr mousedown.dtr mouseup.dtr', selector, function (e) {
				// If the table is not collapsed (i.e. there is no hidden columns)
				// then take no action
				if ( ! $(dt.table().node()).hasClass('collapsed' ) ) {
					return;
				}

				// Check that the row is actually a DataTable's controlled node
				if ( $.inArray( $(this).closest('tr').get(0), dt.rows().nodes().toArray() ) === -1 ) {
					return;
				}

				// For column index, we determine if we should act or not in the
				// handler - otherwise it is already okay
				if ( typeof target === 'number' ) {
					var targetIdx = target < 0 ?
						dt.columns().eq(0).length + target :
						target;

					if ( dt.cell( this ).index().column !== targetIdx ) {
						return;
					}
				}

				// $().closest() includes itself in its check
				var row = dt.row( $(this).closest('tr') );

				// Check event type to do an action
				if ( e.type === 'click' ) {
					// The renderer is given as a function so the caller can execute it
					// only when they need (i.e. if hiding there is no point is running
					// the renderer)
					that._detailsDisplay( row, false );
				}
				else if ( e.type === 'mousedown' ) {
					// For mouse users, prevent the focus ring from showing
					$(this).css('outline', 'none');
				}
				else if ( e.type === 'mouseup' ) {
					// And then re-allow at the end of the click
					$(this).blur().css('outline', '');
				}
			} );
	},


	/**
	 * Get the details to pass to a renderer for a row
	 * @param  {int} rowIdx Row index
	 * @private
	 */
	_detailsObj: function ( rowIdx )
	{
		var that = this;
		var dt = this.s.dt;

		return $.map( this.s.columns, function( col, i ) {
			// Never and control columns should not be passed to the renderer
			if ( col.never || col.control ) {
				return;
			}

			return {
				title:       dt.settings()[0].aoColumns[ i ].sTitle,
				data:        dt.cell( rowIdx, i ).render( that.c.orthogonal ),
				hidden:      dt.column( i ).visible() && !that.s.current[ i ],
				columnIndex: i,
				rowIndex:    rowIdx
			};
		} );
	},


	/**
	 * Find a breakpoint object from a name
	 *
	 * @param  {string} name Breakpoint name to find
	 * @return {object}      Breakpoint description object
	 * @private
	 */
	_find: function ( name )
	{
		var breakpoints = this.c.breakpoints;

		for ( var i=0, ien=breakpoints.length ; i<ien ; i++ ) {
			if ( breakpoints[i].name === name ) {
				return breakpoints[i];
			}
		}
	},


	/**
	 * Re-create the contents of the child rows as the display has changed in
	 * some way.
	 *
	 * @private
	 */
	_redrawChildren: function ()
	{
		var that = this;
		var dt = this.s.dt;

		dt.rows( {page: 'current'} ).iterator( 'row', function ( settings, idx ) {
			var row = dt.row( idx );

			that._detailsDisplay( dt.row( idx ), true );
		} );
	},


	/**
	 * Alter the table display for a resized viewport. This involves first
	 * determining what breakpoint the window currently is in, getting the
	 * column visibilities to apply and then setting them.
	 *
	 * @private
	 */
	_resize: function ()
	{
		var that = this;
		var dt = this.s.dt;
		var width = $(window).width();
		var breakpoints = this.c.breakpoints;
		var breakpoint = breakpoints[0].name;
		var columns = this.s.columns;
		var i, ien;
		var oldVis = this.s.current.slice();

		// Determine what breakpoint we are currently at
		for ( i=breakpoints.length-1 ; i>=0 ; i-- ) {
			if ( width <= breakpoints[i].width ) {
				breakpoint = breakpoints[i].name;
				break;
			}
		}
		
		// Show the columns for that break point
		var columnsVis = this._columnsVisiblity( breakpoint );
		this.s.current = columnsVis;

		// Set the class before the column visibility is changed so event
		// listeners know what the state is. Need to determine if there are
		// any columns that are not visible but can be shown
		var collapsedClass = false;
		for ( i=0, ien=columns.length ; i<ien ; i++ ) {
			if ( columnsVis[i] === false && ! columns[i].never && ! columns[i].control ) {
				collapsedClass = true;
				break;
			}
		}

		$( dt.table().node() ).toggleClass( 'collapsed', collapsedClass );

		var changed = false;
		var visible = 0;

		dt.columns().eq(0).each( function ( colIdx, i ) {
			if ( columnsVis[i] === true ) {
				visible++;
			}

			if ( columnsVis[i] !== oldVis[i] ) {
				changed = true;
				that._setColumnVis( colIdx, columnsVis[i] );
			}
		} );

		if ( changed ) {
			this._redrawChildren();

			// Inform listeners of the change
			$(dt.table().node()).trigger( 'responsive-resize.dt', [dt, this.s.current] );

			// If no records, update the "No records" display element
			if ( dt.page.info().recordsDisplay === 0 ) {
				$('td', dt.table().body()).eq(0).attr('colspan', visible);
			}
		}
	},


	/**
	 * Determine the width of each column in the table so the auto column hiding
	 * has that information to work with. This method is never going to be 100%
	 * perfect since column widths can change slightly per page, but without
	 * seriously compromising performance this is quite effective.
	 *
	 * @private
	 */
	_resizeAuto: function ()
	{
		var dt = this.s.dt;
		var columns = this.s.columns;

		// Are we allowed to do auto sizing?
		if ( ! this.c.auto ) {
			return;
		}

		// Are there any columns that actually need auto-sizing, or do they all
		// have classes defined
		if ( $.inArray( true, $.map( columns, function (c) { return c.auto; } ) ) === -1 ) {
			return;
		}

		// Need to restore all children. They will be reinstated by a re-render
		if ( ! $.isEmptyObject( _childNodeStore ) ) {
			$.each( _childNodeStore, function ( key ) {
				var idx = key.split('-');

				_childNodesRestore( dt, idx[0]*1, idx[1]*1 );
			} );
		}

		// Clone the table with the current data in it
		var tableWidth   = dt.table().node().offsetWidth;
		var columnWidths = dt.columns;
		var clonedTable  = dt.table().node().cloneNode( false );
		var clonedHeader = $( dt.table().header().cloneNode( false ) ).appendTo( clonedTable );
		var clonedBody   = $( dt.table().body() ).clone( false, false ).empty().appendTo( clonedTable ); // use jQuery because of IE8

		// Header
		var headerCells = dt.columns()
			.header()
			.filter( function (idx) {
				return dt.column(idx).visible();
			} )
			.to$()
			.clone( false )
			.css( 'display', 'table-cell' )
			.css( 'min-width', 0 );

		// Body rows - we don't need to take account of DataTables' column
		// visibility since we implement our own here (hence the `display` set)
		$(clonedBody)
			.append( $(dt.rows( { page: 'current' } ).nodes()).clone( false ) )
			.find( 'th, td' ).css( 'display', '' );

		// Footer
		var footer = dt.table().footer();
		if ( footer ) {
			var clonedFooter = $( footer.cloneNode( false ) ).appendTo( clonedTable );
			var footerCells = dt.columns()
				.footer()
				.filter( function (idx) {
					return dt.column(idx).visible();
				} )
				.to$()
				.clone( false )
				.css( 'display', 'table-cell' );

			$('<tr/>')
				.append( footerCells )
				.appendTo( clonedFooter );
		}

		$('<tr/>')
			.append( headerCells )
			.appendTo( clonedHeader );

		// In the inline case extra padding is applied to the first column to
		// give space for the show / hide icon. We need to use this in the
		// calculation
		if ( this.c.details.type === 'inline' ) {
			$(clonedTable).addClass( 'dtr-inline collapsed' );
		}
		
		// It is unsafe to insert elements with the same name into the DOM
		// multiple times. For example, cloning and inserting a checked radio
		// clears the chcecked state of the original radio.
		$( clonedTable ).find( '[name]' ).removeAttr( 'name' );
		
		var inserted = $('<div/>')
			.css( {
				width: 1,
				height: 1,
				overflow: 'hidden',
				clear: 'both'
			} )
			.append( clonedTable );

		inserted.insertBefore( dt.table().node() );

		// The cloned header now contains the smallest that each column can be
		headerCells.each( function (i) {
			var idx = dt.column.index( 'fromVisible', i );
			columns[ idx ].minWidth =  this.offsetWidth || 0;
		} );

		inserted.remove();
	},

	/**
	 * Set a column's visibility.
	 *
	 * We don't use DataTables' column visibility controls in order to ensure
	 * that column visibility can Responsive can no-exist. Since only IE8+ is
	 * supported (and all evergreen browsers of course) the control of the
	 * display attribute works well.
	 *
	 * @param {integer} col      Column index
	 * @param {boolean} showHide Show or hide (true or false)
	 * @private
	 */
	_setColumnVis: function ( col, showHide )
	{
		var dt = this.s.dt;
		var display = showHide ? '' : 'none'; // empty string will remove the attr

		$( dt.column( col ).header() ).css( 'display', display );
		$( dt.column( col ).footer() ).css( 'display', display );
		dt.column( col ).nodes().to$().css( 'display', display );

		// If the are child nodes stored, we might need to reinsert them
		if ( ! $.isEmptyObject( _childNodeStore ) ) {
			dt.cells( null, col ).indexes().each( function (idx) {
				_childNodesRestore( dt, idx.row, idx.column );
			} );
		}
	},


	/**
	 * Update the cell tab indexes for keyboard accessibility. This is called on
	 * every table draw - that is potentially inefficient, but also the least
	 * complex option given that column visibility can change on the fly. Its a
	 * shame user-focus was removed from CSS 3 UI, as it would have solved this
	 * issue with a single CSS statement.
	 *
	 * @private
	 */
	_tabIndexes: function ()
	{
		var dt = this.s.dt;
		var cells = dt.cells( { page: 'current' } ).nodes().to$();
		var ctx = dt.settings()[0];
		var target = this.c.details.target;

		cells.filter( '[data-dtr-keyboard]' ).removeData( '[data-dtr-keyboard]' );

		var selector = typeof target === 'number' ?
			':eq('+target+')' :
			target;

		// This is a bit of a hack - we need to limit the selected nodes to just
		// those of this table
		if ( selector === 'td:first-child, th:first-child' ) {
			selector = '>td:first-child, >th:first-child';
		}

		$( selector, dt.rows( { page: 'current' } ).nodes() )
			.attr( 'tabIndex', ctx.iTabIndex )
			.data( 'dtr-keyboard', 1 );
	}
} );


/**
 * List of default breakpoints. Each item in the array is an object with two
 * properties:
 *
 * * `name` - the breakpoint name.
 * * `width` - the breakpoint width
 *
 * @name Responsive.breakpoints
 * @static
 */
Responsive.breakpoints = [
	{ name: 'desktop',  width: Infinity },
	{ name: 'tablet-l', width: 1024 },
	{ name: 'tablet-p', width: 768 },
	{ name: 'mobile-l', width: 480 },
	{ name: 'mobile-p', width: 320 }
];


/**
 * Display methods - functions which define how the hidden data should be shown
 * in the table.
 *
 * @namespace
 * @name Responsive.defaults
 * @static
 */
Responsive.display = {
	childRow: function ( row, update, render ) {
		if ( update ) {
			if ( $(row.node()).hasClass('parent') ) {
				row.child( render(), 'child' ).show();

				return true;
			}
		}
		else {
			if ( ! row.child.isShown()  ) {
				row.child( render(), 'child' ).show();
				$( row.node() ).addClass( 'parent' );

				return true;
			}
			else {
				row.child( false );
				$( row.node() ).removeClass( 'parent' );

				return false;
			}
		}
	},

	childRowImmediate: function ( row, update, render ) {
		if ( (! update && row.child.isShown()) || ! row.responsive.hasHidden() ) {
			// User interaction and the row is show, or nothing to show
			row.child( false );
			$( row.node() ).removeClass( 'parent' );

			return false;
		}
		else {
			// Display
			row.child( render(), 'child' ).show();
			$( row.node() ).addClass( 'parent' );

			return true;
		}
	},

	// This is a wrapper so the modal options for Bootstrap and jQuery UI can
	// have options passed into them. This specific one doesn't need to be a
	// function but it is for consistency in the `modal` name
	modal: function ( options ) {
		return function ( row, update, render ) {
			if ( ! update ) {
				// Show a modal
				var close = function () {
					modal.remove(); // will tidy events for us
					$(document).off( 'keypress.dtr' );
				};

				var modal = $('<div class="dtr-modal"/>')
					.append( $('<div class="dtr-modal-display"/>')
						.append( $('<div class="dtr-modal-content"/>')
							.append( render() )
						)
						.append( $('<div class="dtr-modal-close">&times;</div>' )
							.click( function () {
								close();
							} )
						)
					)
					.append( $('<div class="dtr-modal-background"/>')
						.click( function () {
							close();
						} )
					)
					.appendTo( 'body' );

				$(document).on( 'keyup.dtr', function (e) {
					if ( e.keyCode === 27 ) {
						e.stopPropagation();

						close();
					}
				} );
			}
			else {
				$('div.dtr-modal-content')
					.empty()
					.append( render() );
			}

			if ( options && options.header ) {
				$('div.dtr-modal-content').prepend(
					'<h2>'+options.header( row )+'</h2>'
				);
			}
		};
	}
};


var _childNodeStore = {};

function _childNodes( dt, row, col ) {
	var name = row+'-'+col;

	if ( _childNodeStore[ name ] ) {
		return _childNodeStore[ name ];
	}

	// https://jsperf.com/childnodes-array-slice-vs-loop
	var nodes = [];
	var children = dt.cell( row, col ).node().childNodes;
	for ( var i=0, ien=children.length ; i<ien ; i++ ) {
		nodes.push( children[i] );
	}

	_childNodeStore[ name ] = nodes;

	return nodes;
}

function _childNodesRestore( dt, row, col ) {
	var name = row+'-'+col;

	if ( ! _childNodeStore[ name ] ) {
		return;
	}

	var node = dt.cell( row, col ).node();
	var store = _childNodeStore[ name ];
	var parent = store[0].parentNode;
	var parentChildren = parent.childNodes;
	var a = [];

	for ( var i=0, ien=parentChildren.length ; i<ien ; i++ ) {
		a.push( parentChildren[i] );
	}

	for ( var j=0, jen=a.length ; j<jen ; j++ ) {
		node.appendChild( a[j] );
	}

	_childNodeStore[ name ] = undefined;
}


/**
 * Display methods - functions which define how the hidden data should be shown
 * in the table.
 *
 * @namespace
 * @name Responsive.defaults
 * @static
 */
Responsive.renderer = {
	listHiddenNodes: function () {
		return function ( api, rowIdx, columns ) {
			var ul = $('<ul data-dtr-index="'+rowIdx+'" class="dtr-details"/>');
			var found = false;

			var data = $.each( columns, function ( i, col ) {
				if ( col.hidden ) {
					$(
						'<li data-dtr-index="'+col.columnIndex+'" data-dt-row="'+col.rowIndex+'" data-dt-column="'+col.columnIndex+'">'+
							'<span class="dtr-title">'+
								col.title+
							'</span> '+
						'</li>'
					)
						.append( $('<span class="dtr-data"/>').append( _childNodes( api, col.rowIndex, col.columnIndex ) ) )// api.cell( col.rowIndex, col.columnIndex ).node().childNodes ) )
						.appendTo( ul );

					found = true;
				}
			} );

			return found ?
				ul :
				false;
		};
	},

	listHidden: function () {
		return function ( api, rowIdx, columns ) {
			var data = $.map( columns, function ( col ) {
				return col.hidden ?
					'<li data-dtr-index="'+col.columnIndex+'" data-dt-row="'+col.rowIndex+'" data-dt-column="'+col.columnIndex+'">'+
						'<span class="dtr-title">'+
							col.title+
						'</span> '+
						'<span class="dtr-data">'+
							col.data+
						'</span>'+
					'</li>' :
					'';
			} ).join('');

			return data ?
				$('<ul data-dtr-index="'+rowIdx+'" class="dtr-details"/>').append( data ) :
				false;
		}
	},

	tableAll: function ( options ) {
		options = $.extend( {
			tableClass: ''
		}, options );

		return function ( api, rowIdx, columns ) {
			var data = $.map( columns, function ( col ) {
				return '<tr data-dt-row="'+col.rowIndex+'" data-dt-column="'+col.columnIndex+'">'+
						'<td>'+col.title+':'+'</td> '+
						'<td>'+col.data+'</td>'+
					'</tr>';
			} ).join('');

			return $('<table class="'+options.tableClass+' dtr-details" width="100%"/>').append( data );
		}
	}
};

/**
 * Responsive default settings for initialisation
 *
 * @namespace
 * @name Responsive.defaults
 * @static
 */
Responsive.defaults = {
	/**
	 * List of breakpoints for the instance. Note that this means that each
	 * instance can have its own breakpoints. Additionally, the breakpoints
	 * cannot be changed once an instance has been creased.
	 *
	 * @type {Array}
	 * @default Takes the value of `Responsive.breakpoints`
	 */
	breakpoints: Responsive.breakpoints,

	/**
	 * Enable / disable auto hiding calculations. It can help to increase
	 * performance slightly if you disable this option, but all columns would
	 * need to have breakpoint classes assigned to them
	 *
	 * @type {Boolean}
	 * @default  `true`
	 */
	auto: true,

	/**
	 * Details control. If given as a string value, the `type` property of the
	 * default object is set to that value, and the defaults used for the rest
	 * of the object - this is for ease of implementation.
	 *
	 * The object consists of the following properties:
	 *
	 * * `display` - A function that is used to show and hide the hidden details
	 * * `renderer` - function that is called for display of the child row data.
	 *   The default function will show the data from the hidden columns
	 * * `target` - Used as the selector for what objects to attach the child
	 *   open / close to
	 * * `type` - `false` to disable the details display, `inline` or `column`
	 *   for the two control types
	 *
	 * @type {Object|string}
	 */
	details: {
		display: Responsive.display.childRow,

		renderer: Responsive.renderer.listHidden(),

		target: 0,

		type: 'inline'
	},

	/**
	 * Orthogonal data request option. This is used to define the data type
	 * requested when Responsive gets the data to show in the child row.
	 *
	 * @type {String}
	 */
	orthogonal: 'display'
};


/*
 * API
 */
var Api = $.fn.dataTable.Api;

// Doesn't do anything - work around for a bug in DT... Not documented
Api.register( 'responsive()', function () {
	return this;
} );

Api.register( 'responsive.index()', function ( li ) {
	li = $(li);

	return {
		column: li.data('dtr-index'),
		row:    li.parent().data('dtr-index')
	};
} );

Api.register( 'responsive.rebuild()', function () {
	return this.iterator( 'table', function ( ctx ) {
		if ( ctx._responsive ) {
			ctx._responsive._classLogic();
		}
	} );
} );

Api.register( 'responsive.recalc()', function () {
	return this.iterator( 'table', function ( ctx ) {
		if ( ctx._responsive ) {
			ctx._responsive._resizeAuto();
			ctx._responsive._resize();
		}
	} );
} );

Api.register( 'responsive.hasHidden()', function () {
	var ctx = this.context[0];

	return ctx._responsive ?
		$.inArray( false, ctx._responsive.s.current ) !== -1 :
		false;
} );

Api.registerPlural( 'columns().responsiveHidden()', 'column().responsiveHidden()', function () {
	return this.iterator( 'column', function ( settings, column ) {
		return settings._responsive ?
			settings._responsive.s.current[ column ] :
			false;
	}, 1 );
} );


/**
 * Version information
 *
 * @name Responsive.version
 * @static
 */
Responsive.version = '2.2.1';


$.fn.dataTable.Responsive = Responsive;
$.fn.DataTable.Responsive = Responsive;

// Attach a listener to the document which listens for DataTables initialisation
// events so we can automatically initialise
$(document).on( 'preInit.dt.dtr', function (e, settings, json) {
	if ( e.namespace !== 'dt' ) {
		return;
	}

	if ( $(settings.nTable).hasClass( 'responsive' ) ||
		 $(settings.nTable).hasClass( 'dt-responsive' ) ||
		 settings.oInit.responsive ||
		 DataTable.defaults.responsive
	) {
		var init = settings.oInit.responsive;

		if ( init !== false ) {
			new Responsive( settings, $.isPlainObject( init ) ? init : {}  );
		}
	}
} );


return Responsive;
}));


