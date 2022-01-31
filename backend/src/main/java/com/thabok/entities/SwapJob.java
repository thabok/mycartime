package com.thabok.entities;

public class SwapJob {

	public Party originalParty;
	public Party preferredParty;
	public Person swapper;
	public Person swappee;

	public SwapJob(Party party, Party preferredParty, Person swapper, Person swappee) {
		this.originalParty = party;
		this.preferredParty = preferredParty;
		this.swapper = swapper;
		this.swappee = swappee;
	}
	
	/**
	 * Performs the swap
	 */
	public void swappediswap() {
		// remove swapper and swappee from their parties
		originalParty.removePassenger(swapper);
		preferredParty.removePassenger(swappee);
		
		// add them to the other party respectively
		preferredParty.addPassenger(swapper);
		originalParty.addPassenger(swappee);
	}
	
}
