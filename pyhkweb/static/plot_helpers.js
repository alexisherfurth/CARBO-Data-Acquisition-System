
var month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// Modified version of Dygraph.numericTicks
function customNumericTicks(a, b, pixels, opts, dygraph, vals) 
{
	ticks = Dygraph.numericTicks(a, b, pixels, opts, dygraph, vals);
	
	var nticks = ticks.length;

	// Check whether or not the tick labels should have an offset
	var offset_metric = Math.log10(Math.abs((a+b)/(a-b)));
	
	//~ console.log(offset_metric);
	
	if (offset_metric > 2.0)
	{
		// Look for the first tick that shows up on the plot
		var i0 = 0;
			while (ticks[i0].v < a || ticks[i0].label.length < 1)
			i0 += 1;
		
		// Show the approximate offset as the first label, and bold it
		offset = ticks[i0].v;
		ticks[i0].label = "<b>&asymp;" + pretty_si(offset, 2, true) + "</b>";
		
		// Show the rest of the labels as deltas with better precision
		for (var i = i0 + 1; i < nticks; i++)
		{
			// Most log plot ticks are blank, so don't apply a label
			if (ticks[i].label.length > 0)
				ticks[i].label = "+" + pretty_si(ticks[i].v - offset, 4, true);
		}
		
		// Make sure to blank out any extra ticks below the offset label,
		// one would sneak through on occasion
		for (var i = 0; i < i0; i++)
			ticks[i].label = '';

	}
	else
	{
		for (var i = 0; i < nticks; i++)
		{
			// Most log plot ticks are blank, so don't apply a label
			if (ticks[i].label.length > 0)
				ticks[i].label = pretty_si(ticks[i].v, 4, true);
		}

	}

	return ticks;
};


// Print a number with SI prefixes and as few digits as needed
si_prefix = ['a','f','p','n','&mu;','m','','k','M','G','T','P','E','Z','Y'];
si_decade = [-18,-15,-12,-9,-6,-3,0,3,6,9,12,15,18,21,24];
function pretty_si(val, max_precision=4, drop_zeros=false)
{		
	if (val == 0 || !isFinite(val))
		return val;
	
	var lbl = '';
	
	for (var i = 0; i < si_prefix.length; i++)
	{
		if ((Math.log10(Math.abs(val)) < si_decade[i] + 3) || (i == si_prefix.length-1))
		{
			v = val*(Math.pow(10,-si_decade[i]));
			
			//~ p = precision - Math.max(0, Math.floor(Math.log10(Math.abs(v))));
			//~ p = Math.max(0, p);
			
			lbl = v.toFixed(max_precision);
			
			// Snip off trailing 0's and, if relevant, the decimal point
			if (drop_zeros)
			{
				for (var j = lbl.length-1; j >= 0; j--)
				{
					if (lbl[j] == '0')
						continue
					else if (lbl[j] == '.')
						j--;
					break;
				}
				lbl = lbl.slice(0,j+1);
			}
			
			return lbl + si_prefix[i];
		}
	}
	return "Failed";
}

// https://stackoverflow.com/questions/1573053/javascript-function-to-convert-color-names-to-hex-codes
function convertToHexColor(englishColor) {

	// create a temporary div. 
	var div = $('<div></div>').appendTo("body").css('background-color', englishColor);
	var computedStyle = window.getComputedStyle(div[0]);

	// get computed color.
	var computedColor = computedStyle.backgroundColor;

	// cleanup temporary div.
	div.remove();

	// done.
	return computedColor;

	// The above returns "rgb(R, G, B)" on IE9/Chrome20/Firefox13.
};

// Zero pad on the left.  7 becomes 007 for n=3
function zeropad(v, n=2)
{
	v = String(v);
	if (n > v.length)
		return Array(n-v.length+1).join("0") + v;
	else
		return v;
}

// Modified version of Dygraph.dateAxisLabelFormatter
function formatDate(date, granularity, opts)
{
	var year = date.getFullYear(),
		month = date.getMonth(),
		day = date.getDate(),
		hours = date.getHours(),
		mins = date.getMinutes(),
		secs = date.getSeconds(),
		millis = date.getSeconds();

	if (granularity >= Dygraph.Granularity.DECADAL) 
	{
		return '' + year;
	} 
	else if (granularity >= Dygraph.Granularity.MONTHLY) 
	{
		return month_names[month] + '&#160;' + year;
	}
	else
	{
		var frac = hours * 3600 + mins * 60 + secs + 1e-3 * millis;
		var day_str = month_names[month] + ' ' +  day;
		if (granularity >= Dygraph.Granularity.DAILY) 
		{
			return day_str;
		}
		else
		{
			var sec_str = "";
			if (granularity < Dygraph.Granularity.MINUTELY)
				var sec_str = ":" + zeropad(secs)
			
			var period_str = 'a';
			if (hours >= 12)
			{
				hours -= 12;
				period_str = 'p';
			}

			if (hours == 0)
				hours = 12;
				
			return hours + ":" + zeropad(mins) + sec_str + period_str + "<br>" + day_str;
		}
	}
}

// Plot axis label formatter
function xValueFormatter(ms)
{
	return new Date(ms)
}		
