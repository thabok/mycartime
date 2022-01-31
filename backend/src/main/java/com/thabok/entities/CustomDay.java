package com.thabok.entities;

/**
 * Data class used to store custom preferences for Persons that override what the schedule may say. 
 * @author thabok
 *
 */
public class CustomDay {

	private static final String pattern = "(\\d\\d?)(.*)(\\d\\d)";
	
	public boolean needsCar;
	public boolean skipMorning;
	public boolean skipAfternoon;
	public String customStart = "";
	public String customEnd = "";

	/**
	 * Converts the given String (e.g. "7:55" or "14:20")
	 * into the integer representation used by webuntis.
	 * 
	 * @return the integer representation of the time string
	 */
	public int getCustomStartTimeInteger() {
		int customStartInt = Integer.parseInt(customStart.replaceAll(pattern, "$1$3"));
		// feasability check
		if (customStartInt < 0 || customStartInt > 2359) {
			throw new IllegalArgumentException("Value " + customStartInt + " does match the expected integer time format (0 - 2359)");
		} else {
			return customStartInt;
		}
	}
	
	/**
	 * Converts the given String (e.g. "7:55" or "14:20")
	 * into the integer representation used by webuntis.
	 * 
	 * @return the integer representation of the time string
	 */
	public int getCustomEndTimeInteger() {
		int customEndInt = Integer.parseInt(customEnd.replaceAll(pattern, "$1$3"));
		// feasability check
		if (customEndInt < 0 || customEndInt > 2359) {
			throw new IllegalArgumentException("Value " + customEndInt + " does match the expected integer time format (0 - 2359)");
		} else {
			return customEndInt;
		}
	}
	
}
