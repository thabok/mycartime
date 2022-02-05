package com.thabok.util;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.stream.Collectors;
import java.util.Optional;
import java.util.Set;

import com.thabok.entities.CustomDay;
import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.DayPlan;
import com.thabok.entities.Party;
import com.thabok.entities.PartyTouple;
import com.thabok.entities.Person;
import com.thabok.entities.Schedule;
import com.thabok.entities.Teacher;
import com.thabok.entities.TimingInfo;
import com.thabok.entities.TwoWeekPlan;
import com.thabok.main.Controller;
import com.thabok.untis.Period;

public class Util {

	public static List<DayOfWeekABCombo> weekdayListAB = Arrays.asList(
		new DayOfWeekABCombo(DayOfWeek.MONDAY, true),
		new DayOfWeekABCombo(DayOfWeek.TUESDAY, true),
		new DayOfWeekABCombo(DayOfWeek.WEDNESDAY, true),
		new DayOfWeekABCombo(DayOfWeek.THURSDAY, true),
		new DayOfWeekABCombo(DayOfWeek.FRIDAY, true),
		new DayOfWeekABCombo(DayOfWeek.MONDAY, false),
		new DayOfWeekABCombo(DayOfWeek.TUESDAY, false),
		new DayOfWeekABCombo(DayOfWeek.WEDNESDAY, false),
		new DayOfWeekABCombo(DayOfWeek.THURSDAY, false),
		new DayOfWeekABCombo(DayOfWeek.FRIDAY, false)
	);

	/**
	 * Array of lesson start times. Note that access is zero-based while lessons are one-based!
	 */
	public static int[] lessonStartTimes = {
			755,  //  1st lesson
			840,  //  2nd lesson
			940,  //  3rd lesson
			1025, //  4th lesson
			1140, //  5th lesson
			1225, //  6th lesson
		  //1310, //  lunch break
			1400, //  7th lesson
			1445, //  8th lesson
			1540, //  9th lesson
			1625, // 10th lesson
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
		for (int i = 0; i < lessonStartTimes.length; i++) {
			if (time <= lessonStartTimes[i]) {
				return i + 1;
			}
		}
		System.out.println("Time " + time + " seems to be kind of late...");
		return 13;
	}
	
	/**
	 * Array of lesson end times. Note that access is zero-based while lessons are one-based!
	 */
	public static int[] lessonEndTimes = {
			840,  //  1st lesson
			940,  //  2nd lesson
			1025, //  3rd lesson
			1140, //  4th lesson
			1225, //  5th lesson
			1310, //  6th lesson
			//1400, //  lunch break
			1445, //  7th lesson
			1530, //  8th lesson
			1625, // 9th lesson
			1710, // 10th lesson
	};
	
	/**
	 * Uses the lesson end times to figure out what lesson the person ends with.
	 * The time must be lower or equal to the next lesson's end time.<br><br>
	 * Example:<br>
	 * <ul>
	 *   <li>1000 would mean finishing after the 3rd lesson</li>
	 *   <li>1030 is after the 4th lesson (not <= 1025)</li>
	 * </ul>
	 * @param time the integer value of the end time, e.g. 1255 for 12:55h
	 * @return the number of the lesson the person ends with (1-13)
	 */
	public static int convertLeavingTimeToLesson(int time) {
		for (int i = 0; i < lessonEndTimes.length; i++) {
			if (time <= lessonEndTimes[i]) {
				return i + 1;  // return value + 1 (lessons are one-based)
			}
		}
		System.out.println("Time " + time + " seems to be kind of late...");
		return lessonEndTimes.length + 1; // return value + 1 (lessons are one-based)
	}
	
	/**
	 * Converts a timetable with start & end time information into a {@link Schedule} object
	 * which is based on 1st lesson, 2nd lesson, etc. for easy of use in the planning algorithm.
	 * <br><br>
	 * The conversion considers the lessons start & end times and uses them as thresholds to
	 * convert the continuous time values into discrete lesson numbers.   
	 * @param person the person can override some parts of the schedule based on preferences
	 * @param timetable the timetable object (continuous)
	 * @return the schedule object (discrete)
	 */
	public static Schedule timetableToSchedule(Person person, Map<Integer, Period> timetable) {
		Schedule schedule = new Schedule();
		Map<Integer, TimingInfo> timingInfoPerDay = new HashMap<>();
		for (Entry<Integer, Period> entry : timetable.entrySet()) {
			DayOfWeekABCombo dayOfWeekABCombo = getDayOfWeekABCombo(entry.getKey() /* date */);
			TimingInfo dayInfo = new TimingInfo();
			// apply first & last lesson based on the retrieved timetable
			dayInfo.setStartTime(entry.getValue().startTime);
			dayInfo.setEndTime(entry.getValue().endTime);
			dayInfo.setFirstLesson(convertArrivingTimeToLesson(entry.getValue().startTime));
			dayInfo.setLastLesson(convertLeavingTimeToLesson(entry.getValue().endTime));
			
			// the person may have custom preferences that override the timetable
			applyCustomPreferencesToDayInfo(dayInfo, entry.getKey(), person);
			
			
			timingInfoPerDay.put(dayOfWeekABCombo.getUniqueNumber(), dayInfo);
		}
		schedule.setTimingInfoPerDay(timingInfoPerDay);
		return schedule;
	}

	private static void applyCustomPreferencesToDayInfo(TimingInfo dayInfo, int date, Person person) {
		int daysBetween = getDaysBetweenDateAndReferenceWeekStartDate(date);
		int customDayIndex = daysBetween > 4 ? daysBetween - 2 : daysBetween;
		CustomDay customDayInfo = person.customDays.get(customDayIndex);
		if (!customDayInfo.customStart.isBlank()) {
			dayInfo.setStartTime(customDayInfo.getCustomStartTimeInteger());
			int firstLesson = convertArrivingTimeToLesson(customDayInfo.getCustomStartTimeInteger());
			dayInfo.setFirstLesson(firstLesson);
		}
		if (!customDayInfo.customEnd.isBlank()) {
			dayInfo.setEndTime(customDayInfo.getCustomEndTimeInteger());
			int lastLesson = convertLeavingTimeToLesson(customDayInfo.getCustomEndTimeInteger());
			dayInfo.setLastLesson(lastLesson);
		}
	}
	
	private static int getDaysBetweenDateAndReferenceWeekStartDate(int dateNumber) {
		DateTimeFormatter dtf = DateTimeFormatter.ofPattern("yyyyMMdd");
		LocalDate dateObj = LocalDate.parse(String.valueOf(dateNumber), dtf);
		LocalDate startDate = LocalDate.parse(String.valueOf(Controller.referenceWeekStartDate), dtf);
		int daysBetween = (int) java.time.Period.between(startDate, dateObj).getDays();
		return daysBetween;
	}

	/**
	 * Given a date integer of the kind yyyymmdd (e.g., 20210831 for August 31st 2021) 
	 * this method returns the day of the week.
	 * 
	 * @param date the date integer
	 * @return the day of the week enum
	 */
	private static DayOfWeekABCombo getDayOfWeekABCombo(int dateNumber) {
		int number = getDaysBetweenDateAndReferenceWeekStartDate(dateNumber);
		DayOfWeek dow = Controller.weekdays.get(number % 7);
		boolean isA = number < 7;
		return new DayOfWeekABCombo(dow, isA);
	}
	
	/**
	 * Adds the specified number of days to the date while considering calendar rules.
	 * @param dateNumber the original date number (int)
	 * @param daysToAdd the number of days to add
	 * @return the calculated date
	 */
	public static int calculateDateNumber(int dateNumber, int daysToAdd) {
		DateTimeFormatter dtf = DateTimeFormatter.ofPattern("yyyyMMdd");
		LocalDate dateObj = LocalDate.parse(String.valueOf(dateNumber), dtf);
		LocalDate calculatedDate = dateObj.plusDays(daysToAdd);
		String calculatedDateString = dtf.format(calculatedDate);
		return Integer.parseInt(calculatedDateString);
	}
	
	/**
	 * Returns true if the period is relevant for the carpool planning. False if not.
	 * 
	 * @param period the period to be checked
	 * @param initials initials of the teacher who's schedule is queried
	 * @return true if the period is relevant for the carpool planning. False if not.
	 */
	public static boolean isPeriodRelevant(Period period, String initials) {
		// class trips, excursions, etc. are marked with the code "irregular"
		if ("irregular".equals(period.code)) {
			return false;
		}
		boolean foundDifferentOrgname = false;
		boolean foundMatchingName = false;
		for (Teacher teacher : period.te) {
			if (teacher.orgname != null) {
				if (teacher.orgname.equals(initials)) {
					// the period is handled by the specified teacher
					foundMatchingName = true;
				} else {
					// the period is only handled temporarily by the specified teacher 
					foundDifferentOrgname = true;
				}
			} else if (teacher.name != null && teacher.name.equals(initials)) {
				// the period is handled by the specified teacher
				foundMatchingName = true;
			}
		}
		boolean isIrrelevant = foundDifferentOrgname && !foundMatchingName;
		return !isIrrelevant;
	}

	/**
	 * Returns true if the party is generally available. This is not the case if the driver
	 * has selected to have no passengers for the morning/afternoon.
	 */
	public static boolean partyIsAvailable(Party party) {
		Person driver = party.getDriver();
		int customPreferenceIndex = Util.dowComboToCustomDaysIndex(party.getDayOfTheWeekABCombo());
		// in case of a partyThere: check if driver wants to be alone in the morning
		if (!party.isWayBack() && driver.customDays.get(customPreferenceIndex).skipMorning) {
			return false;
		}
		// in case of a partyBack: check if driver wants to be alone in the afternoon
		if (party.isWayBack() && driver.customDays.get(customPreferenceIndex).skipAfternoon) {
			return false;
		}
		return true;
		
	}

	public static Map<Integer, CustomDay> initializeEmptyCustomDays() {
		Map<Integer, CustomDay> map = new HashMap<>();
		for (int i=0; i<10; i++) {
			map.put(i, new CustomDay());
		}
		return map;
	}

	/**
	 * Converts the {@link DayOfWeekABCombo} unique number into a customDayIndex
	 * (0-based, without weekend gaps)
	 * 
	 * @param dayOfTheWeekABCombo
	 * @return customDayIndex (0 - 9)
	 */
	public static int dowComboToCustomDaysIndex(DayOfWeekABCombo dayOfTheWeekABCombo) {
		int customDaysIndex;
		if (dayOfTheWeekABCombo.getUniqueNumber() <= 5) {
			customDaysIndex = dayOfTheWeekABCombo.getUniqueNumber() - 1;
		} else {
			customDaysIndex = dayOfTheWeekABCombo.getUniqueNumber() - 3;
		}
		return customDaysIndex;
	}
	
	/**
     * Writes the given String to the specified file. Existing files will be
     * overwritten.
     *
     * @param path
     *            the path to the file
     * @param content
     *            the content to write
     */
    public static void writeStringToFile(String path, String content) {
        // write file using utf-8 encoding
        try (OutputStreamWriter osr = new OutputStreamWriter(new FileOutputStream(path), StandardCharsets.UTF_8);
            BufferedWriter writer = new BufferedWriter(osr)) {
            writer.write(content);
            writer.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    
    /**
     * Returns the content of the file as a String.
     *
     * @param path
     *            path to the file
     * @return the content of the file as a String or an empty String if the file is
     *         not available.
     */
    public static String readStringFromFile(String path) {
        StringBuilder sb = new StringBuilder();
        // Read file line by line using uft-8 encoding
        try (InputStreamReader isr = new InputStreamReader(new FileInputStream(path), StandardCharsets.UTF_8);
            BufferedReader reader = new BufferedReader(isr);) {
            while (reader.ready()) {
                sb.append(reader.readLine()).append("\n");
            }
            isr.close();
            reader.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return sb.toString();
    }

	public static boolean drivesOnMirrorDay(Person person, DayPlan referencePlan) {
		return getMirrorDayPartyTouple(person, referencePlan) != null;
	}

	public static PartyTouple getMirrorDayPartyTouple(Person person, DayPlan referencePlan) {
		Optional<PartyTouple> optional = referencePlan.getPartyTouples()
		.stream().filter(refTouple -> person.equals(refTouple.getDriver()))
		.findAny();
		if (optional.isPresent()) {
			return optional.get();
		} else {
			return null;
		}
	}
	
	public static PartyTouple getPartyToupleByDriver(DayPlan dayPlan, Person driver) {
		for (PartyTouple pt : dayPlan.getPartyTouples()) {
			if (pt.getDriver().equals(driver)) {
				return pt;
			}
		}
		return null;
		
	}

	public static Person getDriverWithLowestNumberOfDrives(Set<Person> possibleDrivers,
			Map<Person, Integer> numberOfDrives) {
		Person minNoOfDrivesPerson = possibleDrivers.iterator().next();
		for (Person p : possibleDrivers) {
			if (numberOfDrives.get(p) < numberOfDrives.get(minNoOfDrivesPerson)) {
				minNoOfDrivesPerson = p;
			}
		}
		return minNoOfDrivesPerson;
	}
	
	public static boolean isPersonActiveOnThisDay(Person p, DayOfWeekABCombo dayOfWeekABCombo) {
		return getTimingInfoForDay(p, dayOfWeekABCombo) != null;
	}
	
	public static TimingInfo getTimingInfoForDay(Person p, DayOfWeekABCombo dayOfWeekABCombo) {
		return p.schedule.getTimingInfoPerDay().get(dayOfWeekABCombo.getUniqueNumber());
	}

	public static List<DayOfWeekABCombo> findMirrorDay(TwoWeekPlan wp, Person person) {
		Set<DayOfWeekABCombo> drivingDaysAB = new HashSet<>();
		for (DayPlan dayPlan : wp.getDayPlans().values()) {
			for (PartyTouple pt : dayPlan.getPartyTouples()) {
				if (person.equals(pt.getDriver())) {
					// check if a combo of the same week day (different week) is present in the set
					Optional<DayOfWeekABCombo> optMatch = drivingDaysAB.stream()
							.filter(combo -> combo.getDayOfWeek().equals(dayPlan.getDayOfWeekABCombo().getDayOfWeek()))
							.findAny();
					if (optMatch.isPresent()) {
						drivingDaysAB.remove(optMatch.get());
					} else {            					
						drivingDaysAB.add(dayPlan.getDayOfWeekABCombo());
					}
					break;
				}
			}
		}
		List<DayOfWeekABCombo> mirrorDays = drivingDaysAB.stream()
				.map(combo -> new DayOfWeekABCombo(combo.getDayOfWeek(), !combo.isWeekA()))
				.collect(Collectors.toList());
		return mirrorDays;
	}
	
}
