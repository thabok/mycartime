package com.thabok.entities;

import java.time.DayOfWeek;
import java.util.ArrayList;
import java.util.List;

public class DayPlan {

	private DayOfWeek dayOfWeek;
	private List<PartyTouple> partyTouples = new ArrayList<>();
	
	public DayOfWeek getDayOfWeek() {
		return dayOfWeek;
	}
	public void setDayOfWeek(DayOfWeek dayOfWeek) {
		this.dayOfWeek = dayOfWeek;
	}
	public List<PartyTouple> getPartyTouples() {
		return partyTouples;
	}
	public void setPartyTouples(List<PartyTouple> partyTouples) {
		this.partyTouples = partyTouples;
	}
	public void addPartyTouple(PartyTouple partyTouple) {
		this.partyTouples.add(partyTouple);
	} 
	
    public String toString() {
    	String s = "[" + dayOfWeek + "]\n";
    	for (PartyTouple partyTouple : partyTouples) {
			s += "\t- " + (partyTouple.isDesignatedDriver() ? "* " : "  ") +  String.join("\n\t    ", partyTouple.toString().split("\\n")) + "\n";
		}
    	return s;
    }
}
