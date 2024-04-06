package com.thabok.entities;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class DayPlan {

	public boolean passengersBalanced = false;
	private DayOfWeekABCombo dayOfWeekABCombo;
	private List<PartyTuple> partyTuples = new ArrayList<>();
	public Map<String, Integer> schoolboundTimesByInitials = new HashMap<>();
	public Map<String, Integer> homeboundTimesByInitials = new HashMap<>();
	
	public DayPlan() {
	}
	public DayPlan(DayOfWeekABCombo combo) {
		this.dayOfWeekABCombo = combo;
	}
	public DayOfWeekABCombo getDayOfWeekABCombo() {
		return dayOfWeekABCombo;
	}
	public void setDayOfWeekABCombo(DayOfWeekABCombo dayOfWeekABCombo) {
		this.dayOfWeekABCombo = dayOfWeekABCombo;
	}
	public List<PartyTuple> getPartyTuples() {
		return partyTuples;
	}
	/**
	 * Returns all parties, homebound and schoolbound.
	 */
	public List<Party> getAllParties() {
		List<Party> allParties = new ArrayList<>();
		for (PartyTuple pt : partyTuples) {
			allParties.add(pt.getSchoolboundParty());
			allParties.add(pt.getHomeboundParty());
		}
		return allParties;
	}
	public void setPartyTuples(List<PartyTuple> partyTuples) {
		this.partyTuples = partyTuples;
	}
	public void addPartyTuple(PartyTuple partyTuple) {
		this.partyTuples.add(partyTuple);
	}
	
	public boolean isWeekA() {
		return this.dayOfWeekABCombo.isWeekA();
	}
	
    public String toString() {
    	String s = "[" + dayOfWeekABCombo + "]\n";
    	List<PartyTuple> partyTuplesSorted = partyTuples.stream()
    			.sorted((pt1, pt2) -> pt1.getDriver().toString().compareTo(pt2.getDriver().toString()))
    			.collect(Collectors.toList());
    	for (PartyTuple partyTuple : partyTuplesSorted) {
			s += "\t- " + (partyTuple.isDesignatedDriver() ? "* " : "  ") +  String.join("\n\t    ", partyTuple.toString().split("\\n")) + "\n";
		}
    	return s;
    }
}
