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
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

import com.thabok.entities.CustomDay;
import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.DayPlan;
import com.thabok.entities.MasterPlan;
import com.thabok.entities.NumberOfDrivesStatus;
import com.thabok.entities.PartyTouple;
import com.thabok.entities.Person;
import com.thabok.entities.TwoWeekPlan;
import com.thabok.helper.PartyHelper;

public class Util {

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

	public static boolean drivesOnGivenDay(Person person, DayPlan referencePlan) {
		return PartyHelper.getPartyToupleByPersonAndDay(person, referencePlan) != null;
	}

	public static boolean alreadyCoveredOnGivenDay(Person person, DayPlan referencePlan, boolean isWayBack) {
		boolean isDriver = drivesOnGivenDay(person, referencePlan);
		boolean isPassenger = PartyHelper.getPartyToupleByPassengerAndDay(person, referencePlan, isWayBack) != null;
		return isDriver || isPassenger;
	}
	
	public static boolean alreadyCoveredOnGivenDay(Person person, DayPlan referencePlan) {
		return alreadyCoveredOnGivenDay(person, referencePlan, false) && alreadyCoveredOnGivenDay(person, referencePlan, true);
	}

	public static Person getDriverWithLowestNumberOfDrives(Collection<Person> possibleDrivers,
			Map<Person, Integer> numberOfDrives) {
		Person minNoOfDrivesPerson = possibleDrivers.iterator().next();
		for (Person p : possibleDrivers) {
			if (numberOfDrives.get(p) < numberOfDrives.get(minNoOfDrivesPerson)) {
				minNoOfDrivesPerson = p;
			}
		}
		return minNoOfDrivesPerson;
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

	/**
	 * Additional Planned days are mirror days that have not been processed yet.
	 * The number shall be considered in the planning so that the driver doesn't start parties on other
	 * days and eventually overcaps on driving days.
	 * 
	 * @param wp the week plan
	 * @param weekA true if week a, false if week b
	 * @param persons 
	 * @return a map of persons to the number of additional days to plan with for the specified week
	 */
	public static Map<Person, Integer> calculatePlannedDaysForWeek(TwoWeekPlan wp, boolean weekA, List<Person> persons) {
		Map<Person, List<DayOfWeekABCombo>> personsToDrivingDays = new HashMap<>();
		Map<Person, Integer> plannedDaysForWeek = new HashMap<>();
		// initialize plannedDaysForWeek map
		persons.forEach(p -> {
			plannedDaysForWeek.put(p, 0);
		});
		
		// collect person driving days
		for (DayOfWeekABCombo combo : wp.getWeekDayPermutation()) {
			DayPlan dayPlan  = wp.getDayPlans().get(combo);
			if (dayPlan != null) {
				for (PartyTouple pt : dayPlan.getPartyTouples()) {
					List<DayOfWeekABCombo> list = personsToDrivingDays.get(pt.getDriver());
					if (list == null) {
						list = new ArrayList<>();
					}
					list.add(dayPlan.getDayOfWeekABCombo());
					personsToDrivingDays.put(pt.getDriver(), list);
				}
			}
		}
		
		// check where a mirror day will appear
		for (Entry<Person, List<DayOfWeekABCombo>> entry : personsToDrivingDays.entrySet()) {
			int additionalPlannedDays = 0;
			for (DayOfWeekABCombo combo : wp.getWeekDayPermutation()) {
				// other week
				if (combo.isWeekA() != weekA && entry.getValue().contains(combo)) {
					boolean mirrorComboAvailable = doesListContainDayOfWeekABCombo(entry.getValue(), combo);
					if (!mirrorComboAvailable) {
						additionalPlannedDays++;
					}
				}
			}
			plannedDaysForWeek.put(entry.getKey(), additionalPlannedDays);
		}
		return plannedDaysForWeek;
	}
	
	private static boolean doesListContainDayOfWeekABCombo(List<DayOfWeekABCombo> list, DayOfWeekABCombo combo) {
		for (DayOfWeekABCombo item : list) {
			if (combo.getUniqueNumber() == item.getUniqueNumber()) {
				return true;
			}
		}
		return false;
	}

	public static DayOfWeekABCombo getMirrorCombo(DayOfWeekABCombo combo) {
		for (DayOfWeekABCombo c : weekdayListAB) {
			if (c.getDayOfWeek().equals(combo.getDayOfWeek()) && c.isWeekA() != combo.isWeekA()) {
				return c;
			}
		}
		return null;
	}
	
	// NEW STUFF
	
	public static String summarizeNumberOfDrives(MasterPlan mp, List<Person> persons) {
		String summary = "";
		Map<Person, Integer> numberOfDrives_Total = new NumberOfDrivesStatus(mp, persons).getNumberOfDrives();
		List<Person> personsByLastName = new ArrayList<>(numberOfDrives_Total.keySet());
		// sort by last name
		personsByLastName.sort((p1, p2) -> p1.lastName.compareTo(p2.lastName));
        for (Person p : personsByLastName) {
            String s = "- " + p.getName() + ": " + numberOfDrives_Total.get(p);
            System.out.println(s);
            summary += s + "\n";
        }
        mp.summary = summary;
        return summary;
    }

	public static String getTimeAsString(int time) {
		String timeAs4Chars = String.format("%04d", time);
		String timeString = String.format("%s:%sh", timeAs4Chars.subSequence(0, 2), timeAs4Chars.substring(2, 4));
		return timeString;
	}


	public static CustomDay getCustomDayObject(Person sirDrivesALot, DayOfWeekABCombo dayOfWeekABCombo) {
		int customDaysIndex = dowComboToCustomDaysIndex(dayOfWeekABCombo);
		CustomDay customDay = sirDrivesALot.customDays.get(customDaysIndex);
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


}
