package com.thabok.entities;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import com.thabok.util.Util;

public class NumberOfDrivesStatus {

	private MasterPlan masterPlan;

	public NumberOfDrivesStatus(MasterPlan masterPlan) {
		this.masterPlan = masterPlan;
	}

	public void update(MasterPlan masterPlan) {
		this.masterPlan = masterPlan;
	}

	public Map<Person, Integer> getNumberOfDrives() {
		return getNumberOfDrives(null);
	}

	public Map<Person, Integer> getNumberOfDrives(Boolean isWeekA) {
		Map<Person, Integer> numberOfDrives = new HashMap<>();
		masterPlan.persons.forEach(p -> numberOfDrives.put(p, 0));
		for (DayPlan dp : masterPlan.getDayPlans().values()) {
			boolean skip = (isWeekA != null) && ((dp.getDayOfWeekABCombo().getUniqueNumber() < 8) != isWeekA);
			if (skip)
				continue;
			for (PartyTouple pt : dp.getPartyTouples()) {
				numberOfDrives.put(pt.getDriver(), numberOfDrives.get(pt.getDriver()) + 1);
			}
		}
		return numberOfDrives;
	}

	public List<Person> getPersonsSortedByNumberOfDrive(boolean sortAscending) {
		return getPersonsSortedByNumberOfDrive(sortAscending, null);
	}

	public List<Person> getPersonsSortedByNumberOfDrive(boolean sortAscending, Boolean isWeekA) {
		Map<Person, Integer> numberOfDrives = getNumberOfDrives(isWeekA);
		int sortingFactor = sortAscending ? 1 : -1; // controls asc vs. desc
		List<Person> personsSorted = masterPlan.persons.stream()
				.sorted((p1, p2) -> numberOfDrives.get(p1).compareTo(numberOfDrives.get(p2)) * sortingFactor)
				.collect(Collectors.toList());
		return personsSorted;
	}

	/**
	 * Returns a list of persons sorted in the following way:
	 * <ul>
	 * <li>prefer lower number of drives for the week (specified via the combo param)</li>
	 * <li>if that's equal for two persons: prefer person who drives on the mirror day</li>
	 * <li>if that's equal for two persons: prefer person with lower number of drives (total)</li>
	 * </ul>
	 * @param combo specifies the day (for mirror day calculation) and the week (for week-specific noDrives)
	 * @return A list of persons with the ones in front who are best suited to start a party on the given day 
	 */
	public List<Person> getPersonsSortedByNumberOfDrivesForGivenDay(DayOfWeekABCombo combo) {
		boolean isWeekA = combo.getUniqueNumber() < 8;
		Map<Person, Integer> numberOfDrives = getNumberOfDrives(isWeekA);
		List<Person> personsSorted = masterPlan.persons.stream().sorted((p1, p2) -> {
			int compare = numberOfDrives.get(p1).compareTo(numberOfDrives.get(p2));
			if (compare == 0) {
				// equal... noDrives for the given week. How about mirror days?
				DayOfWeekABCombo mirrorCombo = Util.getMirrorCombo(combo);
				boolean p1DrivesOnMirrorDay = Util.drivesOnGivenDay(p1, masterPlan.get(mirrorCombo.getUniqueNumber()));
				boolean p2DrivesOnMirrorDay = Util.drivesOnGivenDay(p2, masterPlan.get(mirrorCombo.getUniqueNumber()));
				// prioritize person who drives on mirror day
				if (p1DrivesOnMirrorDay && !p2DrivesOnMirrorDay) {
					return -1; // put p1 before p2
				} else if (!p1DrivesOnMirrorDay && p2DrivesOnMirrorDay) {
					return  1; // put p1 after p2
				} else {
					// still equal... decide based on total noDrives
					Map<Person, Integer> numberOfDrives_total = getNumberOfDrives();
					return numberOfDrives_total.get(p1).compareTo(numberOfDrives_total.get(p2));
				}
			}
			return compare;
		}).collect(Collectors.toList());
		return personsSorted;
	}
}
