package com.thabok.util;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

import com.thabok.entities.CustomDay;
import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.DayPlan;
import com.thabok.entities.MasterPlan;
import com.thabok.entities.NumberOfDrivesStatus;
import com.thabok.entities.PartyTuple;
import com.thabok.entities.Person;
import com.thabok.helper.PartyHelper;

public class Util {

	public static int maximumWaitingTimeInMinutes = 30;
	
	public static final List<DayOfWeek> weekdays = Arrays.asList(DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY);

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

	public static PrintStream out;

	
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
    public static void writeStringToFile(String path, Object content) {
        // write file using utf-8 encoding
        try (OutputStreamWriter osr = new OutputStreamWriter(new FileOutputStream(path), StandardCharsets.UTF_8);
            BufferedWriter writer = new BufferedWriter(osr)) {
            writer.write(content.toString());
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
    public static String readStringFromFile(String path) throws IOException {
        StringBuilder sb = new StringBuilder();
        // Read file line by line using uft-8 encoding
        InputStreamReader isr = new InputStreamReader(new FileInputStream(path), StandardCharsets.UTF_8);
        BufferedReader reader = new BufferedReader(isr);
        while (reader.ready()) {
            sb.append(reader.readLine()).append("\n");
        }
        isr.close();
        reader.close();
        return sb.toString();
    }

	public static boolean drivesOnGivenDay(Person person, DayPlan referencePlan) {
		return PartyHelper.getPartyTupleByDriver(referencePlan, person) != null;
	}
	

	public static boolean alreadyCoveredOnGivenDay(Person person, DayPlan referencePlan, boolean isWayBack) {
		boolean isDriver = drivesOnGivenDay(person, referencePlan);
		boolean isPassenger = PartyHelper.getPartyTupleByPassengerAndDay(person, referencePlan, isWayBack) != null;
		return isDriver || isPassenger;
	}
	
	public static boolean alreadyCoveredOnGivenDay(Person person, DayPlan referencePlan) {
		return alreadyCoveredOnGivenDay(person, referencePlan, false) && alreadyCoveredOnGivenDay(person, referencePlan, true);
	}

	public static Person getPersonWithLowestNumberOfDrives(Collection<Person> possibleDrivers,
			Map<Person, Integer> numberOfDrives) {
		Person minNoOfDrivesPerson = possibleDrivers.iterator().next();
		for (Person p : possibleDrivers) {
			if (numberOfDrives.get(p) < numberOfDrives.get(minNoOfDrivesPerson)) {
				minNoOfDrivesPerson = p;
			}
		}
		return minNoOfDrivesPerson;
	}
	
	public static DayOfWeekABCombo getMirrorCombo(DayOfWeekABCombo combo) {
		for (DayOfWeekABCombo c : weekdayListAB) {
			if (c.getDayOfWeek().equals(combo.getDayOfWeek()) && c.isWeekA() != combo.isWeekA()) {
				return c;
			}
		}
		return null;
	}
	
	public static String getTimeAsString(int time) {
		String timeAs4Chars = String.format("%04d", time);
		String timeString = String.format("%s:%sh", timeAs4Chars.subSequence(0, 2), timeAs4Chars.substring(2, 4));
		return timeString;
	}


	public static CustomDay getCustomDayObject(Person person, DayOfWeekABCombo dayOfWeekABCombo) {
		int customDaysIndex = dowComboToCustomDaysIndex(dayOfWeekABCombo);
		CustomDay customDay = person.customDays.get(customDaysIndex);
		return customDay;
	}


	/**
	 * Returns the first person from the list that is not contained in the set of coveredPersons. May be null if everyone was covered.
	 * @param frequentDriversSortedDesc
	 * @param coveredPersons
	 * @return
	 */
	public static Person getNextUnhandledDriver(List<Person> frequentDriversSortedDesc, Set<Person> coveredPersons) {
		Optional<Person> findFirst = frequentDriversSortedDesc.stream().filter(p -> !coveredPersons.contains(p)).findFirst();
		return findFirst.get();
	}

	/**
	 * Returns a list of days where the given person<br>
	 * - drives<br>
	 * - is not the designated driver<br>
	 * - doesn't drive on the mirror day<br>
	 * 
	 * @param theMasterPlan
	 * @param p
	 * @return list of day plans, may be empty
	 */
	public static List<DayPlan> getNonMirroredDays(MasterPlan theMasterPlan, Person p) {
		List<DayPlan> nonMirroredDays = theMasterPlan.getDayPlans().values().stream().filter(dp -> {
				DayPlan mirrorDp = theMasterPlan.getDayPlans().get(Util.getMirrorCombo(dp.getDayOfWeekABCombo()).getUniqueNumber());
				PartyTuple pt = PartyHelper.getPartyTupleByDriver(dp, p);
				boolean drivesOnThisDay = pt != null;
				boolean isDesignatedDriverOnThisDay = pt != null && pt.isDesignatedDriver();
				boolean drivesOnMirrorDay = Util.drivesOnGivenDay(p, mirrorDp);
				return drivesOnThisDay && !isDesignatedDriverOnThisDay && drivesOnMirrorDay;
			}).collect(Collectors.toList());
		return nonMirroredDays;
	}
	
	/**
	 * Returns a list of days where the given person<br>
	 * - doesn't drive<br>
	 * - but drives on the mirror day<br>
	 * 
	 * @param theMasterPlan
	 * @param p
	 * @return list of day plans, may be empty
	 */
	public static List<DayPlan> getMissingMirrorDays(MasterPlan theMasterPlan, Person p) {
		List<DayPlan> missingMirrorDays = theMasterPlan.getDayPlans().values().stream().filter(dp -> {
				DayPlan mirrorDp = theMasterPlan.getDayPlans().get(Util.getMirrorCombo(dp.getDayOfWeekABCombo()).getUniqueNumber());
				PartyTuple pt = PartyHelper.getPartyTupleByDriver(dp, p);
				boolean drivesOnThisDay = pt != null;
				boolean drivesOnMirrorDay = Util.drivesOnGivenDay(p, mirrorDp);
				return !drivesOnThisDay && drivesOnMirrorDay;
			}).collect(Collectors.toList());
		return missingMirrorDays;
	}
	

	public static String summarizeNumberOfDrives(MasterPlan mp) {
		String summary = "";
		Map<Person, Integer> numberOfDrives_Total = new NumberOfDrivesStatus(mp).getNumberOfDrives();
		List<Person> personsByLastName = new ArrayList<>(numberOfDrives_Total.keySet());
		// sort by last name
		personsByLastName.sort((p1, p2) -> {
			int comp = numberOfDrives_Total.get(p1).compareTo(numberOfDrives_Total.get(p2));
			if (comp == 0) {
				comp = p1.lastName.compareTo(p2.lastName);
			}
			return comp;
		});
        for (Person p : personsByLastName) {
            String s = "- " + p.toString() + ": " + numberOfDrives_Total.get(p);
            summary += s + "\n";
        }
        mp.summary = summary;
        return summary;
    }


	public static void printDrivingDaysAbMap(MasterPlan theMasterPlan) {
		Map<Person, Integer> numberOfDrives = new NumberOfDrivesStatus(theMasterPlan).getNumberOfDrives();
		List<Person> personsByLastName = new ArrayList<>(theMasterPlan.persons);
		// sort by last name
		personsByLastName.sort((p1, p2) -> {
			int comp = numberOfDrives.get(p1).compareTo(numberOfDrives.get(p2));
			if (comp == 0) {
				comp = p1.lastName.compareTo(p2.lastName);
			}
			return comp;
		});
		for (Person person : personsByLastName) {
			String spaces = "";
			for (int i=0; i<(19 - person.firstName.length()); i++) {
				spaces += " ";
			}
			out.println(String.format("|  %s: %s%s|", person, numberOfDrives.get(person), spaces));
			PartyTuple pt = PartyHelper.getPartyTupleByDriver(theMasterPlan.getDayPlans().get(1), person);
			boolean monA = pt != null;
			boolean desigMonA = pt != null && pt.isDesignatedDriver();
			pt = PartyHelper.getPartyTupleByDriver(theMasterPlan.getDayPlans().get(2), person);
			boolean tueA = pt != null;
			boolean desigTueA = pt != null && pt.isDesignatedDriver();
			pt = PartyHelper.getPartyTupleByDriver(theMasterPlan.getDayPlans().get(3), person);
			boolean wedA = pt != null;
			boolean desigWedA = pt != null && pt.isDesignatedDriver();
			pt = PartyHelper.getPartyTupleByDriver(theMasterPlan.getDayPlans().get(4), person);
			boolean thuA = pt != null;
			boolean desigThuA = pt != null && pt.isDesignatedDriver();
			pt = PartyHelper.getPartyTupleByDriver(theMasterPlan.getDayPlans().get(5), person);
			boolean friA = pt != null;
			boolean desigFriA = pt != null && pt.isDesignatedDriver();
			pt = PartyHelper.getPartyTupleByDriver(theMasterPlan.getDayPlans().get(8), person);
			boolean monB = pt != null;
			boolean desigMonB = pt != null && pt.isDesignatedDriver();
			pt = PartyHelper.getPartyTupleByDriver(theMasterPlan.getDayPlans().get(9), person);
			boolean tueB = pt != null;
			boolean desigTueB = pt != null && pt.isDesignatedDriver();
			pt = PartyHelper.getPartyTupleByDriver(theMasterPlan.getDayPlans().get(10), person);
			boolean wedB = pt != null;
			boolean desigWedB = pt != null && pt.isDesignatedDriver();
			pt = PartyHelper.getPartyTupleByDriver(theMasterPlan.getDayPlans().get(11), person);
			boolean thuB = pt != null;
			boolean desigThuB = pt != null && pt.isDesignatedDriver();
			pt = PartyHelper.getPartyTupleByDriver(theMasterPlan.getDayPlans().get(12), person);
			boolean friB = pt != null;
			boolean desigFriB = pt != null && pt.isDesignatedDriver();
			out.println("| MON | TUE | WED | THU | FRI |");
			out.println(String.format("|  %s  |  %s  |  %s  |  %s  |  %s  |", getAbMapMark(monA, desigMonA), getAbMapMark(tueA, desigTueA), getAbMapMark(wedA, desigWedA), getAbMapMark(thuA, desigThuA) ,getAbMapMark(friA, desigFriA)));
			out.println(String.format("|  %s  |  %s  |  %s  |  %s  |  %s  |", getAbMapMark(monB, desigMonB), getAbMapMark(tueB, desigTueB), getAbMapMark(wedB, desigWedB), getAbMapMark(thuB, desigThuB) ,getAbMapMark(friB, desigFriB)));
			out.println();
		}
	}
	
	private static String getAbMapMark(boolean isDriving, boolean isDesignatedDriver) {
		if (isDesignatedDriver) {
			return "*";
		} else if (isDriving) {
			return "x";
		} else {
			return " ";
		}
	}


	/**
	 * Returns true if the difference between time1 and time2 is less or equal to the maximumWaitingTimeInMinutes (default 30)
	 */
	public static boolean isTimeDifferenceAcceptable(int time1, int time2 /* , Person waitingPerson, DayOfWeekABCombo dayOfWeek, boolean homebound*/) {
		//if (homebound && waitingPerson.customDays.get(dayOfWeek.getUniqueNumber()).noWaitingAfternoon) {
		//	System.out.println("Time difference not acceptable due to custom prefs of " + waitingPerson.initials);
		//	return false;
		//}
		return maximumWaitingTimeInMinutes >= getTimeDifference(time1, time2);
	}

	/**
	 * Returns the time difference between time1 and time 2 while considering that there are 5 minutes between 755 and 800, not 45.
	 * @param time1 int value of time1
	 * @param time2 int value of time2
	 * @return netto diff value in minutes
	 */
	public static int getTimeDifference(int time1, int time2) {
		int biggy = time1 > time2 ? time1 : time2;
		int lowie = time1 < time2 ? time1 : time2;
		int diff = biggy - lowie;
		int factor = 0;
		if ((lowie % 100) > (biggy % 100)) {
			factor++;
		}
		if (diff >= 40) {
			diff = diff - ((diff / 100) + factor) * 40;
		}
		return diff;		
	}

	public static List<Person> getListThatContainsThisPerson(Map<Integer, List<Person>> personsByFirstLesson,
			Person person) {
		for (List<Person> list : personsByFirstLesson.values()) {
			if (list.contains(person)) {
				return list;
			}
		}
		return Collections.emptyList();
		
	}


    public static int getRefComboInt(int uniqueNumber) {
        return uniqueNumber > 5 ? uniqueNumber - 7 : uniqueNumber + 7;
    }


//	public static void main(String[] args) {
//	}
}
