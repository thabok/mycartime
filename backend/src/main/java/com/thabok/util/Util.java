package com.thabok.util;

import java.time.DayOfWeek;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import com.thabok.entities.Schedule;
import com.thabok.entities.TimingInfo;
import com.thabok.main.Controller;
import com.thabok.untis.TimetableItem;

public class Util {

	public static int[] lessonStartTimes = {
			755,  //  1st lesson
			840,  //  2nd lesson
			940,  //  3rd lesson
			1025, //  4th lesson
			1140, //  5th lesson
			1225, //  6th lesson
			1310, //  7th lesson
			1400, //  8th lesson
			1445, //  9th lesson
			1540, // 10th lesson
			1625, // 11th lesson
			1730  // 12th lesson
	};

	/**
	 * Uses the lesson start times to figure out what lesson the person starts with.
	 * The time must be lower or equal to the lesson start time.<br><br>
	 * Example:<br>
	 * <ul>
	 *   <li>800 would be in time for the second lesson because it's <= 840</li>
	 *   <li>It's not in time for the first lesson though (not <= 755)</li>
	 * </ul>
	 * @param time the integer value of the start time, e.g. 755 for 7:55h
	 * @return the number of the lesson the person starts with (1-13)
	 */
	public static int convertArrivingTimeToLesson(int time) {
		for (int i = 1; i <= lessonStartTimes.length; i++) {
			if (time <= lessonStartTimes[i]) {
				return i;
			}
		}
		System.out.println("Time " + time + " seems to be kind of late...");
		return 13;
	}
	
	public static int[] lessonEndTimes = {
			840,  //  1st lesson
			940,  //  2nd lesson
			1025, //  3rd lesson
			1140, //  4th lesson
			1225, //  5th lesson
			1310, //  6th lesson
			1400, //  7th lesson
			1445, //  8th lesson
			1540, //  9th lesson
			1625, // 10th lesson
			1730, // 11th lesson
			1815, // 12th lesson
	};
	
	/**
	 * Uses the lesson start times to figure out what lesson the person ends with.
	 * The time must be lower or equal to the next lesson's start time.<br><br>
	 * Example:<br>
	 * <ul>
	 *   <li>1000 would mean finishing after the 3rd lesson</li>
	 *   <li>1030 is after the 4th lesson (not <= 1025)</li>
	 * </ul>
	 * @param time the integer value of the end time, e.g. 1255 for 12:55h
	 * @return the number of the lesson the person starts with (1-13)
	 */
	public static int convertLeavingTimeToLesson(int time) {
		for (int i = 1; i <= lessonStartTimes.length; i++) {
			if (time <= lessonStartTimes[i]) {
				return i;
			}
		}
		System.out.println("Time " + time + " seems to be kind of late...");
		return 13;
	}
	
	/**
	 * Converts a timetable with start & end time information into a {@link Schedule} object
	 * which is based on 1st lesson, 2nd lesson, etc. for easy of use in the planning algorithm.
	 * <br><br>
	 * The conversion considers the lessons start & end times and uses them as thresholds to
	 * convert the continuous time values into discrete lesson numbers.   
	 * 
	 * @param timetable the timetable object (continuous)
	 * @return the schedule object (discrete)
	 */
	public static Schedule timetableToSchedule(Map<Integer, TimetableItem> timetable) {
		Schedule schedule = new Schedule();
		List<Entry<Integer, TimetableItem>> entries = new ArrayList<>(timetable.entrySet());
		if (entries.size() != Controller.weekdays.size()) {
			throw new IllegalArgumentException("The timetable doesn't contain information for every day.");
		}
		Map<DayOfWeek, TimingInfo> timingInfoPerDay = new HashMap<>();
		for (int i = 0; i < entries.size(); i++) {
			TimetableItem item = entries.get(i).getValue();
			DayOfWeek dayOfWeek = Controller.weekdays.get(i);
			TimingInfo dayInfo = new TimingInfo();
			dayInfo.setFirstLesson(convertArrivingTimeToLesson(item.startTime));
			dayInfo.setLastLesson(convertArrivingTimeToLesson(item.endTime));
			timingInfoPerDay.put(dayOfWeek, dayInfo);
		}
		schedule.setTimingInfoPerDay(timingInfoPerDay);
		return schedule;
	}
	
}
