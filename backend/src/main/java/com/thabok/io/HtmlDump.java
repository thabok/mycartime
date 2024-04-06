package com.thabok.io;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.stream.Collectors;

import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.DayPlan;
import com.thabok.entities.DayPlanInput;
import com.thabok.entities.MasterPlan;
import com.thabok.entities.Party;
import com.thabok.entities.PartyTuple;
import com.thabok.entities.Person;
import com.thabok.util.Util;

public class HtmlDump {

	private static final String TOKEN_COMBO = "__COMBO__";
	private static final String TOKEN_SB_POOL = "__SB_POOL__";
	private static final String TOKEN_SB_PLAN = "__SB_PLAN__";
	private static final String TOKEN_HB_POOL = "__HB_POOL__";
	private static final String TOKEN_HB_PLAN = "__HB_PLAN__";
	static String htmlTemplate = 	"<table border=\"1\">\n" +
									"    <colgroup>\n" +
									"    <col style='width: 12%;'>\n" +
									"    <col style='width: 22%;'>\n" +
									"    <col style='width: 22%;'>\n" +
									"    <col style='width: 22%;'>\n" +
									"    <col style='width: 22%;'>\n" +
									"    </colgroup>\n" +
									"    <tr>\n" +
									"    <th rowspan=\"3\">" + TOKEN_COMBO + "</th>\n" +
									"    <th colspan=\"2\">Schoolbound</th>\n" +
									"    <th colspan=\"2\">Homebound</th>\n" +
									"</tr>\n" +
									"<tr>\n" +
									"    <td>Pool</td>\n" +
									"    <td>Plan</td>\n" +
									"    <td>Pool</td>\n" +
									"    <td>Plan</td>\n" +
									"</tr>\n" +
									"<tr>\n" +
									"    <td>" + TOKEN_SB_POOL + "</td>\n" +
									"    <td>" + TOKEN_SB_PLAN + "</td>\n" +
									"    <td>" + TOKEN_HB_POOL + "</td>\n" +
									"    <td>" + TOKEN_HB_PLAN + "</td>\n" +
									"</tr>\n" +
									"</table>\n" +
									"<br/>\n\n";
	
	public static void toHtml(MasterPlan mp, String filepath) {
		
		if (!Util.out.equals(System.out)) { return; }
		
		// create day plan dumps for easier data handling
		List<DayPlan_Dump> dayPlanDumps = new ArrayList<>();
		List<DayOfWeekABCombo> daysSorted = Util.weekdayListAB.stream().sorted().collect(Collectors.toList());
		for (DayOfWeekABCombo combo : daysSorted) {
			DayPlanInput dayPlanInput = mp.inputsPerDay.get(combo.getUniqueNumber());
			DayPlan dayPlan = mp.getDayPlans().get(combo.getUniqueNumber());
			dayPlanDumps.add(new DayPlan_Dump(dayPlanInput, dayPlan, combo));
		}
		
		StringBuilder sb = new StringBuilder();
		
		/*
		 *  dump data into HTML file
		 */
		for (DayPlan_Dump dpd : dayPlanDumps) {
			String comboString = dpd.combo.toString().substring(0,3).toUpperCase();
			comboString += dpd.combo.isWeekA() ? "_A" : "_B";
			String schoolboundPoolString = createPoolString(dpd.schoolboundPool);
			String schoolboundPlanString = createPlanString(dpd.schoolboundPlan);
			String homeboundPoolString = createPoolString(dpd.homeboundPool);
			String homeboundPlanString = createPlanString(dpd.homeboundPlan);
			sb.append(htmlTemplate
					.replace(TOKEN_COMBO, comboString)
					.replace(TOKEN_SB_POOL, schoolboundPoolString)
					.replace(TOKEN_SB_PLAN, schoolboundPlanString)
					.replace(TOKEN_HB_POOL, homeboundPoolString)
					.replace(TOKEN_HB_PLAN, homeboundPlanString));
		}
		
		Util.writeStringToFile(filepath, sb.toString());
		
	}

	private static String createPlanString(List<Plan_Dump> schoolboundPlan) {
		List<String> planLines = schoolboundPlan.stream().map(plan -> {
			String timeAsString = Util.getTimeAsString(plan.time);
			List<Person> persons = new ArrayList<>();
			persons.add(plan.driver.person);
			persons.addAll(plan.passengers);
			List<String> allPersonsNamesAndInitials = persons.stream().map(p -> p.firstName + " (" + p.initials + ")").collect(Collectors.toList());
			String personsString = String.join(", ", allPersonsNamesAndInitials);
			String line = "[" + timeAsString + "] ";
			if (plan.driver.isDesignatedDriver) {
				line += "*";
			}
			line += personsString;
			return line;
		}).collect(Collectors.toList());
		return String.join("<br/>", planLines);
	}

	private static String createPoolString(List<Pool_Dump> poolDumpSlots) {
		List<String> poolLines = poolDumpSlots.stream().map(poolDumpSlot -> {
			String timeAsString = Util.getTimeAsString(poolDumpSlot.time);
			List<String> personsNamesAndInitials = poolDumpSlot.persons.stream().map(p -> p.person.firstName + " (" + p.person.initials + ")").collect(Collectors.toList());
			String personsString = String.join(", ", personsNamesAndInitials);
			return "[" + timeAsString + "] " + personsString;
		}).collect(Collectors.toList());
		return String.join("<br/>", poolLines);
	}
	
	
}

class DayPlan_Dump {

	DayOfWeekABCombo combo;
	List<Pool_Dump> schoolboundPool;
	List<Plan_Dump> schoolboundPlan;
	List<Pool_Dump> homeboundPool;
	List<Plan_Dump> homeboundPlan;
	
	DayPlan_Dump(DayPlanInput dpi, DayPlan dayPlan, DayOfWeekABCombo combo) {
		this.combo = combo;
		this.schoolboundPlan = populatePlan(dpi, dayPlan, true);
		this.homeboundPlan = populatePlan(dpi, dayPlan, false);
		
		Set<Person> schoolboundCoveredPersons = new HashSet<>();
		schoolboundPlan.stream().forEach(plan -> {
			schoolboundCoveredPersons.add(plan.driver.person);
			schoolboundCoveredPersons.addAll(plan.passengers);
		});
		
		Set<Person> homeboundCoveredPersons = new HashSet<>();
		homeboundPlan.stream().forEach(plan -> {
			homeboundCoveredPersons.add(plan.driver.person);
			homeboundCoveredPersons.addAll(plan.passengers);
		});
		
		this.schoolboundPool = populatePool(dpi, true, schoolboundCoveredPersons);
		this.homeboundPool = populatePool(dpi, false, homeboundCoveredPersons);
	}
	
	
	List<Pool_Dump> populatePool(DayPlanInput dpi, boolean isSchoolbound, Set<Person> coveredPersons) {
		List<Pool_Dump> pool = new ArrayList<>();
		Map<Integer, List<Person>> personsByTime = isSchoolbound ? dpi.personsByFirstLesson : dpi.personsByLastLesson;
		for (Entry<Integer, List<Person>> entry : personsByTime.entrySet()) {
			List<Person_Dump> personsOfSameTime = new ArrayList<>();
			for (Person p : entry.getValue()) {
				if (!coveredPersons.contains(p)) {
					// only show persons in pool that are not yet part of the plan
					personsOfSameTime.add(new Person_Dump(p, entry.getKey(), dpi.designatedDrivers.contains(p)));
				}
			}
			if (!personsOfSameTime.isEmpty()) {
				pool.add(new Pool_Dump(entry.getKey(), personsOfSameTime));
			}
		}
		Collections.sort(pool, (a, b) -> Integer.compare(a.time, b.time));
		return pool;
	}
	
	List<Plan_Dump> populatePlan(DayPlanInput dpi, DayPlan dayPlan, boolean isSchoolbound) {
		List<Plan_Dump> plan = new ArrayList<>();
		for (PartyTuple pt : dayPlan.getPartyTuples()) {
			Party party = isSchoolbound ? pt.getSchoolboundParty() : pt.getHomeboundParty();
			boolean isDesignatedDriver = dpi.designatedDrivers.contains(party.getDriver());
			Plan_Dump partyDump = new Plan_Dump(party, isDesignatedDriver);
			plan.add(partyDump);
		}
		Collections.sort(plan, (a, b) -> Integer.compare(a.time, b.time));
		return plan;
	}
	
}


class Person_Dump {
	
	Person_Dump(Person person, int time, boolean isDesignatedDriver) {
		this.person = person;
		this.time = time;
		this.isDesignatedDriver = isDesignatedDriver;
	}
	
	Person person;
	int time;
	boolean isDesignatedDriver;
	
	public String toString() {
		return (isDesignatedDriver ? "*" : "") + person.toString() + " (" + Util.getTimeAsString(time) + ")";
	}
	
}

class Pool_Dump {
	
	Pool_Dump(int time, List<Person_Dump> persons) {
		this.persons = persons;
		this.time = time;
	}
	
	List<Person_Dump> persons;
	int time;
	
	public String toString() {
		return "[" + Util.getTimeAsString(time) + "] " + persons.toString();
	}
	
}

class Plan_Dump {
	
	public Plan_Dump(Party p, boolean isDesignatedDriver) {
		this.time = p.getTime();
		this.driver = new Person_Dump(p.getDriver(), p.getTime(), isDesignatedDriver);
		this.passengers = p.getPassengers();
	}
	
	Person_Dump driver;
	int time;
	List<Person> passengers;
	
	public String toString() {
		return "[" + Util.getTimeAsString(time) + "] " + (driver.isDesignatedDriver ? "*" : "") + driver.person.toString() + ", " + passengers.toString();
	}
}