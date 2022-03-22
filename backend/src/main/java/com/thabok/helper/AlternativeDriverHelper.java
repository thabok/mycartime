package com.thabok.helper;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Optional;

import com.thabok.entities.CustomDay;
import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.DayPlan;
import com.thabok.entities.DayPlanInput;
import com.thabok.entities.MasterPlan;
import com.thabok.entities.NumberOfDrivesStatus;
import com.thabok.entities.PartyTouple;
import com.thabok.entities.Person;
import com.thabok.util.Constants;
import com.thabok.util.Util;

/**
 * Static helper class for finding alternative drivers for people who would otherwise drive too often.
 * This is done by merging first lesson + early hall duty.
 * 
 * @author thabok
 */
public class AlternativeDriverHelper {

	/**
	 * Finds alternative drivers for people who would otherwise drive too often.
	 * This is done by merging first lesson + early hall duty.
	 * 
	 * @param theMasterPlan
	 * @param persons
	 * @param inputsPerDay
	 * @throws Exception 
	 */
	public static void findAlternativeForSirDrivesALots(MasterPlan theMasterPlan, List<Person> persons, Map<Integer, DayPlanInput> inputsPerDay) throws Exception {
		Map<Person, Integer> numberOfDrives = new NumberOfDrivesStatus(theMasterPlan, persons).getNumberOfDrives();
		for (Entry<Person, Integer> entry : numberOfDrives.entrySet()) {
			Integer drivingDays = entry.getValue();
			if (drivingDays > Constants.EXPECTED_DRIVING_DAYS_THRESHOLD) { // persons a lot of drives
				Person sirDrivesALot = entry.getKey();
				List<DayPlan> prioritizedDrivingDays = new ArrayList<>();
				List<DayPlan> otherDrivingDays = new ArrayList<>();
				// prioritize to remove days without matching mirror day drives
				for (DayPlan dayPlan : theMasterPlan.getDayPlans().values()) {
					DayOfWeekABCombo mirrorCombo = Util.getMirrorCombo(dayPlan.getDayOfWeekABCombo());
					DayPlan mirrorDayPlan = theMasterPlan.get(mirrorCombo.getUniqueNumber());
					CustomDay customDayConfig = Util.getCustomDayObject(sirDrivesALot, dayPlan.getDayOfWeekABCombo());
					boolean drivesOnGivenDay = Util.drivesOnGivenDay(sirDrivesALot, dayPlan);
					boolean drivesOnMirrorDay = Util.drivesOnGivenDay(sirDrivesALot, mirrorDayPlan);
					boolean doesntNeedTheCar = !customDayConfig.needsCar;
					if (drivesOnGivenDay && doesntNeedTheCar) {
						if (!drivesOnMirrorDay) {
							// prioritize to try to get rid of this day
							prioritizedDrivingDays.add(dayPlan);
						} else {
							otherDrivingDays.add(mirrorDayPlan);
						}
					}
				}
				prioritizedDrivingDays.addAll(otherDrivingDays);
				// pDD now contains all days with prio days in the front
				Person alternativeDriver = tryToFindAlternativeDriver(theMasterPlan, sirDrivesALot, prioritizedDrivingDays, persons, inputsPerDay);
				if (alternativeDriver == null) {
					System.err.println("Didn't find anyone to take over for " + sirDrivesALot);
				}
			}
		}
	}
	
	/*
	 * Private methods
	 */
	
	/**
	 * Tries to find an alternative driver for one of the given driving days. Method returns as soon as one alternative has been found.
	 * @param theMasterPlan 
	 * @param sirDrivesALot the driver with too many driving days
	 * @param prioritizedDrivingDays the days he drives on, sorted by prio (unmatched days first)
	 * @param persons everyone (incl. the driver)
	 * @param inputsPerDay 
	 * @return
	 * @throws Exception 
	 */
	private static Person tryToFindAlternativeDriver(MasterPlan theMasterPlan, Person sirDrivesALot, List<DayPlan> prioritizedDrivingDays,
			List<Person> persons, Map<Integer, DayPlanInput> inputsPerDay) throws Exception {
		AlternativeDriverConfig alternativeDriverCfg = null;
		// iterate over driving days starting with the prioritized ones (given by order)
		for (DayPlan dayPlan : prioritizedDrivingDays) {
			DayOfWeekABCombo combo = dayPlan.getDayOfWeekABCombo();
			DayPlanInput dpi = inputsPerDay.get(combo.getUniqueNumber());
			int personsWithSameLastLesson = dpi.personsByLastLesson.get(sirDrivesALot.getTimeForDowCombo(combo, true)).size();
			int startTime = sirDrivesALot.getTimeForDowCombo(combo, false);
			boolean startsAtFirstLessonOrEarlier = startTime <= Constants.FIRST_LESSON_START_TIME;
			boolean firstLessonIsTheReasonSirDrivesALotMustDrive = personsWithSameLastLesson > 1;
			// if the criteria is met, collect alternative candidates
			if (startsAtFirstLessonOrEarlier && firstLessonIsTheReasonSirDrivesALotMustDrive) {
				List<AlternativeDriverConfig> alternateDriverCandidates = new ArrayList<>();
				for (Person alternativeDriverCandidate : persons) {
					boolean notActiveOnThatDay = !TimetableHelper.isPersonActiveOnThisDay(alternativeDriverCandidate, combo);
					boolean samePerson = alternativeDriverCandidate.equals(sirDrivesALot);
					boolean alreadyDrivingTooOften = new NumberOfDrivesStatus(theMasterPlan, persons).getNumberOfDrives().get(alternativeDriverCandidate) > Constants.EXPECTED_DRIVING_DAYS_THRESHOLD;
					if (samePerson || notActiveOnThatDay || alreadyDrivingTooOften) {
						// alternativeDriver is not suitable:
						continue;
					}
					int altStartTime = alternativeDriverCandidate.getTimeForDowCombo(combo, false);
					if (altStartTime <= Constants.FIRST_LESSON_START_TIME) {
						// found an alternative driver
						AlternativeDriverConfig cfg = new AlternativeDriverConfig();
						cfg.alternativeDriver = alternativeDriverCandidate;
						cfg.dayPlan = dayPlan;
						cfg.originalStartTime = startTime;
						cfg.altStartTime = altStartTime;
						alternateDriverCandidates.add(cfg);
					}
				}
				// if candidates are available: pick the candidate with the lowest number of drives
				if (!alternateDriverCandidates.isEmpty()) {
					// sort so that candidates with low number of drives are at the beginning
					alternateDriverCandidates.sort((c1, c2) -> {
						Map<Person, Integer> numberOfDrives = new NumberOfDrivesStatus(theMasterPlan, persons).getNumberOfDrives();;
						return numberOfDrives.get(c1.alternativeDriver).compareTo(numberOfDrives.get(c2.alternativeDriver));
					});
					alternativeDriverCfg = alternateDriverCandidates.get(0);
					break;
				}
			} // else: ignore, only merge early hall duty with normal first lesson starts
		}
		
		// if we have an alternativeDriver
		if (alternativeDriverCfg != null) {
			DayPlan relevantPlan = alternativeDriverCfg.dayPlan;
			Person alternativeDriver = alternativeDriverCfg.alternativeDriver;
			System.out.println(String.format("Found an alternative driver: %s (%s) can take over for %s (%s) on %s",
					alternativeDriver, Util.getTimeAsString(alternativeDriverCfg.altStartTime), 
					sirDrivesALot, Util.getTimeAsString(alternativeDriverCfg.originalStartTime),
					relevantPlan.getDayOfWeekABCombo()));
			// Get PartyTouple of SirDrivesALot to remove it:
			Optional<PartyTouple> optional = relevantPlan.getPartyTouples().stream().filter(pt -> pt.getDriver().equals(sirDrivesALot)).findAny();
			if (optional.isEmpty()) {
				throw new IllegalStateException("Cannot find a party where sir drives a lot drives... that can't be right?!");
			}
			// remove sirDrivesALot's party touple
			relevantPlan.getPartyTouples().remove(optional.get());
			
			// add party for the alternative driver
			PartyHelper.addSoloParty(relevantPlan, alternativeDriver, false, inputsPerDay, theMasterPlan.getDayPlans());
			return alternativeDriver; // may be null
		} else {
			return null;
		}
	}
	
	
}

class AlternativeDriverConfig {
	DayPlan dayPlan;
	Person alternativeDriver;
	int originalStartTime;
	int altStartTime;
}

